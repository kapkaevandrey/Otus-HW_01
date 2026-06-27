# Отчёт и инструкция для проверяющего

Домашнее задание: декомпозиция монолита социальной сети — выделен **chat-service** (диалоги), синхронизация пользователей через **transactional outbox + Kafka**.

## Репозитории

| Репозиторий | Назначение | Порт API |
|-------------|------------|----------|
| **Otus-HW_01** (монолит) | пользователи, друзья, посты, лента, WS; **прокси API диалогов** | `8000` |
| **Otus-HW-chats** | диалоги (Redis), inbox пользователей (PostgreSQL), consumer `cud.user` | `8001` |

---

## Что реализовано

### 1. Выделение chat-service

- Отдельный репозиторий `Otus-HW-chats`: REST `/api/v1/dialog/{user_id}/send|list`, Valkey для сообщений, PostgreSQL для локальной копии пользователей.
- Монолит **не хранит диалоги** — проксирует запросы в chat-service по HTTP (`ChatServiceClient`).

### 2. Синхронизация пользователей (transactional outbox)

В монолите при `add` / `update` / `remove` на таблице `users`:

1. Изменение в `users` (в той же транзакции).
2. Запись в `users_outbox` (`action` + `data` JSONB, без пароля).
3. Фоновая задача `processing_users_outbox_task` читает outbox (`FOR UPDATE SKIP LOCKED`), публикует в Kafka топик **`cud.user`**, удаляет обработанную запись.

Chat-service: `UserConsumer` на топике `cud.user` → upsert/delete в таблице `users`.

Формат сообщения:

```json
{
  "action": "create",
  "data": {
    "id": "uuid",
    "first_name": "...",
    "second_name": "...",
    "birthdate": "1990-01-01",
    "biography": null,
    "city": null
  }
}
```

### 3. API диалогов в монолите (обратная совместимость)

Старые эндпоинты **сохранены** (`/api/v1/dialog/...`):

| Method | Path | Поведение |
|--------|------|-----------|
| POST | `/api/v1/dialog/{user_id}/send` | прокси в chat-service |
| GET | `/api/v1/dialog/{user_id}/list` | прокси в chat-service |

- **Успешный ответ** — сырой JSON от chat-service (`JSONResponse`), без Pydantic-валидации (схемы только для Swagger).
- **Ошибка chat-service** — разбирается в `BaseServiceError` (статус, message, details) и отдаётся в формате монолита через `HTTPException`.
- Заголовок **`X-Request-Id`** пробрасывается в chat-service.

### 4. Прочее

- `RequestIdMiddleware` в обоих сервисах.
- Postman-коллекция: `docs/postman/Otus_socal.postman_collection.json`.
- Smoke-тест E2E: `scripts/e2e_smoke.sh`.

---

## Схема взаимодействия

```
Клиент
  │
  ├─ POST /api/v1/user/register ──► монолит (users + users_outbox)
  │                                      │
  │                                      ▼
  │                               Kafka: cud.user
  │                                      │
  │                                      ▼
  │                               chat-service (users inbox)
  │
  ├─ POST /api/v1/dialog/.../send ──► монолит ──HTTP──► chat-service (Redis)
  │
  └─ POST :8001/api/v1/dialog/.../send ───────────────► chat-service напрямую
```

---

## Требования к окружению

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) (для локального запуска chat-service)
- `curl`, `psql` (опционально, для проверки sync)
- Python **3.14**

---

## Запуск для проверки (рекомендуемый сценарий)

Общая Kafka и Redis монолита; у chat-service — **свои** PostgreSQL и Valkey (порты не конфликтуют).

### Шаг 1. Монолит (инфраструктура + API)

```bash
cd Otus-HW_01
WORKERS=1 docker compose up -d --scale worker=1 --scale app-instance=0 --build
```

> **Важно:** `WORKERS=1` — иначе `citus-init` может долго ждать воркеры и блокировать `migrate`/`app`.

Проверка:

```bash
curl http://localhost:8000/healthz   # "OK"
open http://127.0.0.1:8000/docs
```

Если `migrate` не отработал (завис на `citus-init`):

```bash
docker exec otus-hw_01-app-1 uv run alembic upgrade head
docker compose up -d --no-deps --force-recreate app
```

Swagger монолита: http://127.0.0.1:8000/docs

| Сервис | Порт |
|--------|------|
| API монолита | 8000 |
| PostgreSQL (Citus) | 5432 |
| Valkey | 6379 |
| Kafka | 9092 |
| Kafka UI | 8082 |

### Шаг 2. Chat-service — инфраструктура (БД + Redis)

Kafka **не поднимаем** — используем Kafka монолита на `localhost:9092`.

```bash
cd Otus-HW-chats
docker compose -p chats-e2e -f docker-compose.yaml -f docker-compose.e2e.yaml up -d db valkey
docker compose -p chats-e2e -f docker-compose.yaml -f docker-compose.e2e.yaml run --rm redis-script-loader
```

Миграции (локально, БД на порту **5433**):

```bash
cp .env.example .env   # или создать .env — см. ниже
uv sync
uv run alembic upgrade head
```

Пример `.env` для **локального** запуска app:

```env
DEBUG=true
JWT_PRIVATE_KEY=secret
JWT_PUB_KEY=secret
DB_MASTER_HOST=localhost
DB_MASTER_PORT=5433
DB_MASTER_PASSWORD=app_pswd
DB_DATABASE=chats
KAFKA_BROKERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6380
```

JWT-ключи должны совпадать с монолитом (`dev.env`: `JWT_*=secret`).

### Шаг 3. Chat-service — приложение (в консоли)

```bash
cd Otus-HW-chats
uv run uvicorn app.server:app --host 0.0.0.0 --port 8001
```

Проверка:

```bash
curl http://localhost:8001/healthz   # "OK"
open http://127.0.0.1:8001/docs
```

В `docker-compose.yaml` монолита уже задано:

```yaml
CHAT_SERVICE_URL: http://host.docker.internal:8001
```

(контейнер app обращается к chat-service на хосте).

---

## Сценарии проверки

### 1. Регистрация и синхронизация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/user/register \
  -H 'Content-Type: application/json' \
  -d '{
    "first_name": "Ivan",
    "second_name": "Petrov",
    "birthdate": "1990-05-15",
    "biography": "test",
    "city": "Moscow",
    "password": "E2eTest1!Pass"
  }'
```

Сохранить `user_id` из ответа. Через несколько секунд пользователь должен появиться в БД chat-service:

```bash
PGPASSWORD=app_pswd psql -h localhost -p 5433 -U postgres -d chats \
  -c "SELECT id, first_name FROM users WHERE first_name = 'Ivan';"
```

Дополнительно: Kafka UI http://localhost:8082 — топик `cud.user`.

### 2. Логин и получение токена

```bash
curl -X POST http://localhost:8000/api/v1/login \
  -H 'Content-Type: application/json' \
  -d '{"id": "<USER_ID>", "password": "E2eTest1!Pass"}'
```

Токен для заголовка: **`access_token.token`** из JSON (не весь объект `access_token`).

```bash
export TOKEN="<access_token.token>"
```

### 3. Старый API диалогов (монолит, прокси)

Зарегистрировать **двух** пользователей, дождаться sync, залогиниться от имени первого:

```bash
# отправка
curl -X POST "http://localhost:8000/api/v1/dialog/<USER_B_ID>/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text": "hello via monolith"}'

# список сообщений
curl "http://localhost:8000/api/v1/dialog/<USER_B_ID>/list" \
  -H "Authorization: Bearer $TOKEN"
```

Ожидается `200` и JSON с полями `"from"`, `"to"`, `"text"`, `"sent_at"`.

### 4. Новый API диалогов (chat-service напрямую)

Тот же JWT, но запрос на `:8001`:

```bash
curl -X POST "http://localhost:8001/api/v1/dialog/<USER_A_ID>/send" \
  -H "Authorization: Bearer $TOKEN_B" \
  -H 'Content-Type: application/json' \
  -d '{"text": "hello via chat"}'

curl "http://localhost:8001/api/v1/dialog/<USER_A_ID>/list" \
  -H "Authorization: Bearer $TOKEN_B"
```

Оба пользователя должны быть в inbox chat-service, иначе будет `404` / ошибка «user not found».

### 5. Автоматический smoke-тест

После запуска обоих сервисов:

```bash
cd Otus-HW_01
bash scripts/e2e_smoke.sh
```

---

## Остановка

```bash
# монолит
cd Otus-HW_01 && docker compose down

# chat infra
cd Otus-HW-chats && docker compose -p chats-e2e down

# chat app — Ctrl+C в терминале с uvicorn
```

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `citus-init` не завершается | `WORKERS=1`, перезапуск; app поднять с `--no-deps --force-recreate` |
| Outbox-таски падают «relation users_outbox does not exist» | `docker exec otus-hw_01-app-1 uv run alembic upgrade head` |
| Пользователь не появляется в chat DB | Проверить Kafka (`cud.user`), логи chat-service (`UserConsumer`), что app chat запущен с `KAFKA_BROKERS=localhost:9092` |
| Диалог 401 | В Authorization передавать `access_token.token`, не весь объект |
| Диалог 404 «user not found» в chat | Дождаться sync или проверить consumer |
| Конфликт портов Kafka/Redis | Chat-service infra поднимать с `-p chats-e2e` и `docker-compose.e2e.yaml`; Kafka только у монолита |

---

## Тесты разработчика

```bash
# монолит
cd Otus-HW_01
make install
make pytest          # docker + postgres
make check_code      # ruff + mypy

# chat-service
cd Otus-HW-chats
make install
make pytest
make check_code
```

---

## Ключевые файлы

**Монолит**

- `app/core/repositories/repos/user.py` — outbox при CUD `users`
- `app/core/services/outbox/service.py` — processor `users_outbox` → Kafka
- `app/core/services/dialogs/service.py` — прокси диалогов
- `app/core/clients/http/chats.py` — HTTP-клиент chat-service
- `migrations/versions/2026-06-28_1_add_users_outbox.py`

**Chat-service**

- `app/apps/consumers/user.py` — consumer `cud.user`
- `app/core/services/dialogs/` — логика диалогов в Redis
- `app/server.py` — lifespan + `UserConsumer`
