from functools import cached_property
from typing import Any

from aiokafka import ConsumerRecord
from pydantic import ValidationError

from app.core.clients import BaseKafkaConsumer
from app.core.containers import Context, get_context
from app.schemas.services import InboxWsMessage


class WsMessagesConsumer(BaseKafkaConsumer):
    @cached_property
    def context(self) -> Context:
        return get_context()

    async def process_message(self, message: ConsumerRecord, context: Any = None) -> None:
        schema, _ts_ms = self.try_get_message_schema(message.value), message.timestamp
        if not schema:
            return
        ws = self.context.socket_manager.get_socket_for_session(schema.send_to_user_id)
        if not ws:
            self.logger.info(f"Active websocket for user {schema.send_to_user_id} not found.")
            return
        try:
            await self.context.socket_manager.send_personal_json(schema.payload, ws.ws)
        except Exception as e:
            self.logger.error("Failed to send message to socket", exc_info=e)

    def try_get_message_schema(self, data: bytes | str | dict) -> InboxWsMessage | None:
        try:
            if isinstance(data, (bytes, str)):
                base_message: InboxWsMessage = InboxWsMessage.model_validate_json(data)
            else:
                base_message = InboxWsMessage.model_validate(data)
            return base_message
        except ValidationError as error:
            self.logger.error(
                f"Failed validate base_message data. Data - {data.decode() if isinstance(data, bytes) else data}",
                exc_info=error,
            )
        return None
