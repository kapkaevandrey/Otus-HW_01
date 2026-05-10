import asyncio
from logging import Logger, getLogger

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.enums import WebSocketStatusCodes
from app.core.utils import restart_on_exception
from app.schemas.services import AsyncChannelQueue

from .socket import ActiveWebSocket


SUB_ID = str
WS_KEY = int
USER_ID = str


class SocketConnectionManager:
    DEFAULT_RECEIVED_WAITING_TIMEOUT = 10
    CLEANUP_INTERVAL_SECONDS = 1 * 60
    RETRY_DELAY_SECONDS = 5
    MAX_CLEANUP_RETRIES = 10

    def __init__(self, logger: Logger | None = None) -> None:
        self.active_connections: dict[int, ActiveWebSocket] = {}
        self.active_connections_user_map: dict[USER_ID, WS_KEY] = {}
        self._user_locks: dict[USER_ID, asyncio.Lock] = {}
        self._ws_to_user_id_map: dict[WS_KEY, USER_ID] = {}
        self._cleanup_task: asyncio.Task | None = None
        self.logger = logger or getLogger(__name__)
        # Alembic can disable already-created loggers via logging config.
        # Re-enable this logger so runtime and tests can capture websocket events.
        self.logger.disabled = False

    async def connect_user(
        self,
        user_id: USER_ID,
        websocket: WebSocket,
    ) -> bool:
        async with self._get_user_lock(user_id):
            if await self._is_exists_device_ws(user_id, websocket):
                return False
            await self.connect(websocket)
            ws_key = self.websocket_key(websocket)
            self.active_connections_user_map[user_id] = ws_key
            self._ws_to_user_id_map[ws_key] = user_id
            self.logger.info(f"Connected: User - {user_id}")
            return True

    async def connect(self, websocket: WebSocket) -> None:
        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.accept()
        key = self.websocket_key(websocket)
        self.active_connections[key] = ActiveWebSocket(
            ws=websocket, read_queue=AsyncChannelQueue(queue=asyncio.Queue())
        )
        self.logger.info(f"Connected websocket with key: {key}")

    @staticmethod
    def websocket_key(websocket: WebSocket) -> int:
        return id(websocket)

    def _get_user_lock(self, user_id: USER_ID) -> asyncio.Lock:
        lock = self._user_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._user_locks[user_id] = lock
        return lock

    async def _is_exists_device_ws(self, user_id: USER_ID, websocket: WebSocket) -> bool:
        if (ws_key := self.active_connections_user_map.get(user_id)) is None:
            return False
        existing_ws = self.active_connections.get(ws_key)
        if existing_ws and existing_ws.ws.client_state in (WebSocketState.CONNECTED, WebSocketState.CONNECTING):
            await self.disconnect(
                websocket,
                code=WebSocketStatusCodes.POLICY_VIOLATION,
                reason="Connection for this user/device already exists",
            )
            self.logger.info(
                "Rejected new socket for existing connection: user_id=%s",
                user_id,
            )
            return True
        return False

    def get_session_id(self, user_id: USER_ID) -> int | None:
        return self.active_connections_user_map.get(user_id, None)

    def get_socket_for_session(self, user_id: USER_ID) -> ActiveWebSocket | None:
        ws_id = self.active_connections_user_map.get(user_id, None)
        if ws_id:
            return self.active_connections.get(ws_id)
        return None

    async def disconnect(
        self,
        websocket: WebSocket,
        code: WebSocketStatusCodes | int | None = None,
        reason: str | None = None,
    ) -> None:
        code = code or WebSocketStatusCodes.CLOSE_NORMAL
        key = self.websocket_key(websocket)
        active_connection = self.active_connections.pop(key, None)
        if active_connection:
            await active_connection.stop()
        if websocket.client_state in (WebSocketState.CONNECTED, WebSocketState.CONNECTING):
            await websocket.close(code=code, reason=reason)
            self.logger.info(f"Disconnected Socket: {key} with reason: {reason}")

    async def start(self) -> None:
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(
                restart_on_exception(
                    self.cleanup_connections,
                    run_params={"max_retries": self.MAX_CLEANUP_RETRIES},
                )
            )
            self.logger.info("Clean up not active socket connection task started")

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self.logger.info("Clean up not active socket connection task stoped")
            self._cleanup_task = None

    async def cleanup_connections(
        self,
        max_retries: int,
        unless: bool = True,
        delay: int | float | None = None,
        retry_delay: int | float | None = None,
    ) -> None:
        delay = delay or self.CLEANUP_INTERVAL_SECONDS
        retry_delay = retry_delay or self.RETRY_DELAY_SECONDS
        retries = 0
        run_flag = True
        while run_flag:
            run_flag = unless
            try:
                await self._cleanup_connections()
                retries = 0
            except Exception as error:
                if retries == max_retries:
                    self.logger.critical(
                        f"Failed retry clean up operations after {retries}/{max_retries} retries", exc_info=True
                    )
                    raise error
                retries += 1
                self.logger.error(f"Failed run cleanup task, retrie num {retries}", exc_info=True)
            _delay = delay if not retries else retries * retry_delay
            await asyncio.sleep(_delay)

    async def _cleanup_connections(self):
        disconnected_keys = []
        for key, active_connection in self.active_connections.items():
            if active_connection.ws.client_state != WebSocketState.CONNECTED:
                disconnected_keys.append(key)
        for key in disconnected_keys:
            user_id = self._ws_to_user_id_map.pop(key, None)
            self._user_locks.pop(user_id, None)
            if user_id in self.active_connections_user_map:
                conn = self.active_connections.get(key, None)
                await conn.stop()
                await self.disconnect_user(
                    user_id=user_id,
                    websocket=conn.ws if conn else None,
                )
            self.active_connections.pop(key, None)

    async def disconnect_user(
        self,
        user_id: USER_ID,
        websocket: WebSocket | None,
        code: int | WebSocketStatusCodes | None = None,
        reason: str | None = None,
    ) -> None:
        if not websocket:
            return
        ws_key = self.websocket_key(websocket)
        self.active_connections_user_map.pop(user_id, None)
        self._ws_to_user_id_map.pop(ws_key, None)
        self._user_locks.pop(user_id, None)
        await self.disconnect(websocket, code, reason)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(data=message)

    async def send_personal_json(self, data: list | dict, websocket: WebSocket) -> None:
        await websocket.send_json(data=data)

    async def received_json(self, websocket: WebSocket, timeout: float | None = None) -> dict | None:
        timeout = timeout or self.DEFAULT_RECEIVED_WAITING_TIMEOUT
        try:
            return await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
        except TimeoutError:
            self.logger.error(f"Timeout waiting for websocket to receive json timeout={timeout}")
            return None
