import asyncio
from http import HTTPStatus

from app.core.enums import EventTypes
from app.core.repositories import UnitOfWork
from app.core.services.base import BaseService, async_use_case
from app.exceptions import BaseServiceError
from app.schemas.dto import EventActionOutboxDto
from app.schemas.services import BaseServiceResponse, PostForFriendsEventSchema


class OutboxService(BaseService):
    DEFAULT_DELAY = 5

    async def processing_events_task(
        self,
        *,
        service_name: str,
        topics_map: dict[EventTypes, str],
        delay: float | None = None,
    ) -> None:
        found_items = True
        delay = delay or self.DEFAULT_DELAY
        while True:
            if not found_items:
                await asyncio.sleep(delay)
            async with self.context.uow.transaction() as uow:
                items = await uow.service_event_outbox_repo.get_by_attributes(
                    order_fields=["created_at"], limit=1, lock=True, skip_locked=True
                )
                if not items:
                    self.logger.debug(f"No service events found sleep for {delay} seconds.")
                    found_items = False
                    continue
                found_items = True
                await self.processing_service_events(
                    event=items[0], service_name=service_name, topics_map=topics_map, uow=uow
                )
                await uow.service_event_outbox_repo.remove({"id": items[0].id})

    @async_use_case()
    async def processing_service_events(
        self, event: EventActionOutboxDto, service_name: str, topics_map: dict[EventTypes, str], uow: UnitOfWork
    ) -> BaseServiceResponse[None]:
        response = BaseServiceResponse[None]()
        if event.event_type == EventTypes.SEND_NEW_POST_FOR_FRIENDS:
            await self._processing_send_post_to_friends_event(
                event=event,
                service_name=service_name,
                topics_map=topics_map[EventTypes.SEND_NEW_POST_FOR_FRIENDS],
                uow=uow,
            )
        else:
            message = f"Unknown event type {event.event_type}. Expected {[*EventTypes]}"
            self.logger.warning(message)
            raise BaseServiceError(
                status=HTTPStatus.NOT_IMPLEMENTED, error_message=message, error_details=event.model_dump(mode="json")
            )
        return response

    async def _processing_send_post_to_friends_event(
        self, event: EventActionOutboxDto, service_name: str, topic: str, uow: UnitOfWork
    ) -> None:
        data = PostForFriendsEventSchema.model_validate(event.properties)
        post = await uow.user_publication_repo.get({"id": data.post_id})
        message = {}
        await self.context.kafka_producer.send_message(
            topic=topic, value=message, headers={"source": service_name}, key=post.id.hex
        )
