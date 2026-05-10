# Otus-HW_01
## Инструкция по запуску
### 
## Инструкция по запуску

### Для запуска используйте утилиту make
```shell
make run
```
После запуска swagger локально доступен http://127.0.0.1:8000/docs

### Очистка контейнеров
```shell
make down
```

### Полный список команд
```shell
make help 
```

### Документация и коллекция Postman находиться в директории docs

## WebSocket подключение

Канал обновлений ленты постов:

- URL: `ws://127.0.0.1:8000/post/feed/posted`
- Авторизация: заголовок `Authorization: Bearer <access_token>`
- Токен можно получить через REST `POST /login`

### Пример подключения через Node.js (`ws`)

```javascript
import WebSocket from "ws";

const ws = new WebSocket("ws://127.0.0.1:8000/post/feed/posted", {
  headers: {
    Authorization: "Bearer <access_token>",
  },
});

ws.onopen = () => console.log("ws connected");
ws.onmessage = (event) => console.log("message:", event.data);
ws.onclose = (event) => console.log("ws closed:", event.code, event.reason);
ws.onerror = (error) => console.error("ws error:", error);
```

### Пример подключения через wscat

```shell
wscat -c ws://127.0.0.1:8000/post/feed/posted -H "Authorization: Bearer <access_token>"
```

После подключения сервер отправляет json-сообщения о новых постах друзей.

> В браузерном `WebSocket` нельзя передать `Authorization` header напрямую.

