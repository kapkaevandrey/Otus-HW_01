import datetime as dt
from types import SimpleNamespace
from uuid import uuid4

from app.apps.consumers import CacheFeedConsumer
from app.core.enums import EventTypes
from app.core.services import UserUtils
from app.schemas.services import BaseServiceResponse, ServiceEvent


class StubPostService:
    RECALCULATE_CACHE_EVENTS = {EventTypes.ADD_FRIEND}

    def __init__(self, response: BaseServiceResponse[None] | None = None):
        self.calls: list[dict] = []
        self.response = response or BaseServiceResponse[None]()

    async def recalculate_user_feed_from_event(self, schema: ServiceEvent, user_utils: UserUtils, ts_ms: int):
        self.calls.append({"schema": schema, "user_utils": user_utils, "ts_ms": ts_ms})
        return self.response


def get_consumer_with_service(service: StubPostService) -> CacheFeedConsumer:
    consumer = CacheFeedConsumer(
        consumer_class=object,
        consumer_args=(),
        consumer_kwargs={},
    )
    consumer.__dict__["post_service"] = service
    return consumer


async def test_process_message_calls_recalculate_for_supported_event():
    service = StubPostService()
    consumer = get_consumer_with_service(service)
    message = SimpleNamespace(
        value={
            "event_type": EventTypes.ADD_FRIEND,
            "data": {
                "user_id": str(uuid4()),
                "friend_id": str(uuid4()),
                "created_at": dt.datetime.now(tz=dt.UTC).isoformat(),
            },
        },
        timestamp=1234567890,
    )

    await consumer.process_message(message)

    assert len(service.calls) == 1
    call = service.calls[0]
    assert isinstance(call["schema"], ServiceEvent)
    assert call["schema"].event_type == EventTypes.ADD_FRIEND
    assert isinstance(call["user_utils"], UserUtils)
    assert call["ts_ms"] == message.timestamp


async def test_process_message_skips_unsupported_event():
    service = StubPostService()
    consumer = get_consumer_with_service(service)
    message = SimpleNamespace(
        value={
            "event_type": EventTypes.UPDATE_USER_PUBLICATION,
            "data": {},
        },
        timestamp=1234567890,
    )
    await consumer.process_message(message)
    assert service.calls == []


async def test_process_message_skips_invalid_payload():
    service = StubPostService()
    consumer = get_consumer_with_service(service)
    message = SimpleNamespace(value=b"not-a-json", timestamp=1234567890)
    await consumer.process_message(message)
    assert service.calls == []


async def test_process_message_logs_error_when_recalculate_failed(caplog):
    response = BaseServiceResponse[None]()
    response.set_unsuccessful(error_message="boom", error_detail={"reason": "failed"})
    service = StubPostService(response=response)
    consumer = get_consumer_with_service(service)
    message = SimpleNamespace(
        value={
            "event_type": EventTypes.ADD_FRIEND,
            "data": {
                "user_id": str(uuid4()),
                "friend_id": str(uuid4()),
                "created_at": dt.datetime.now(tz=dt.UTC).isoformat(),
            },
        },
        timestamp=1234567890,
    )
    await consumer.process_message(message)
    assert "Failed to recalculate user feed cache" in caplog.text
