from functools import cached_property
from typing import Any

from aiokafka import ConsumerRecord
from pydantic import ValidationError

from app.core.clients import BaseKafkaConsumer
from app.core.containers import Context, get_context
from app.core.services import PostService, UserUtils
from app.schemas.services import BigCacheFeedRecalculateEvent


class CelebrityFeedConsumer(BaseKafkaConsumer):
    @cached_property
    def post_service(self) -> PostService:
        return PostService(self.context)

    @cached_property
    def context(self) -> Context:
        return get_context()

    async def process_message(self, message: ConsumerRecord, context: Any = None) -> None:
        schema, _ts_ms = self.try_get_message_schema(message.value), message.timestamp
        service_response = await self.post_service.recalculate_celebrity_users_feeds(
            schema=schema, user_utils=UserUtils()
        )
        if service_response.is_success:
            self.logger.info("Successfully recalculated big user feed cache")
        else:
            self.logger.error(
                "Failed to recalculate user feed cache",
                extra={
                    "error_message": service_response.error_message,
                    "error_details": service_response.error_details,
                },
            )

    def try_get_message_schema(self, data: bytes | str | dict) -> BigCacheFeedRecalculateEvent | None:
        try:
            if isinstance(data, (bytes, str)):
                base_message: BigCacheFeedRecalculateEvent = BigCacheFeedRecalculateEvent.model_validate_json(data)
            else:
                base_message = BigCacheFeedRecalculateEvent.model_validate(data)
            return base_message
        except ValidationError as error:
            self.logger.error(
                f"Failed validate base_message data. Data - {data.decode() if isinstance(data, bytes) else data}",
                exc_info=error,
            )
        return None
