# Otus-HW_01 — социальная сеть (монолит)

## Для проверяющего

**Полный отчёт, архитектура и пошаговый запуск:** [docs/REVIEW.md](docs/REVIEW.md)

Кратко: поднять монолит → поднять infra chat-service → запустить chat-service локально на `:8001` → проверить регистрацию, sync, API диалогов (монолит и chat).

## Быстрый старт

```shell
WORKERS=1 docker compose up -d --scale worker=1 --scale app-instance=0
```

Swagger: http://127.0.0.1:8000/docs

```shell
make down   # остановка
make help   # все команды
```

Postman-коллекция: `docs/postman/Otus_socal.postman_collection.json`

## WebSocket (лента постов)

- URL: `ws://127.0.0.1:8000/post/feed/posted`
- Auth: `Authorization: Bearer <access_token.token>`

```shell
wscat -c ws://127.0.0.1:8000/post/feed/posted -H "Authorization: Bearer <token>"
```
