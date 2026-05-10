from logging import getLogger

from app.core.containers import Context
from app.core.enums import EventTypes
from app.core.services import OutboxService


logger = getLogger(__name__)


async def processing_events_outbox_task(
    context: Context,
    service_name: str,
    topics_map: dict[EventTypes, str],
    delay: float | None = None,
) -> None:
    logger.info("Starting processing events outbox task")
    service = OutboxService(context)
    await service.processing_events_task(
        service_name=service_name,
        topics_map=topics_map,
        delay=delay,
    )
