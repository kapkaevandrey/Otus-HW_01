import asyncio
import logging
import ssl
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apps.api import main_router
from app.apps.consumers import CelebrityFeedConsumer, FeedConsumer, WsMessagesConsumer
from app.apps.ws import ws_router
from app.config import app_settings, kafka_settings
from app.core.containers import get_context
from app.core.enums import EventTypes
from app.core.services.tasks import processing_events_outbox_task
from app.core.utils import restart_on_exception, run_tasks, shutdown
from app.logging_config import configure_logging


logger = logging.getLogger(__name__)


def setup_middlewares(application: FastAPI) -> None:
    logger.debug("Setup middlewares")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routers(application: FastAPI) -> None:
    application.include_router(main_router)
    application.include_router(ws_router)


def get_app(app_name: str, lifespan: Callable) -> FastAPI:
    application = FastAPI(
        title=app_name,
        root_path=app_settings.ROOT_PATH,
        debug=app_settings.DEBUG,
        event_manager_queue=asyncio.Queue(),
        statistic_queue=asyncio.Queue(),
        lifespan=lifespan,
    )
    configure_logging(
        root_log_level=app_settings.LOG_LEVEL,
        app_log_level_map={
            "app": "INFO",
            "uvicorn": "INFO",
            "aiokafka": "WARNING",
        },
        log_dev=app_settings.LOG_DEV,
    )
    setup_middlewares(application)
    setup_routers(application)
    return application


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    context = get_context()
    default_consumer_kwargs = {
        "group_id": kafka_settings.KAFKA_GROUP_ID,
        "enable_auto_commit": False,
        "max_poll_interval_ms": kafka_settings.KAFKA_MAX_POOL_INTERVAL,
        "bootstrap_servers": kafka_settings.KAFKA_BROKERS,
        "security_protocol": kafka_settings.KAFKA_SECURITY_PROTOCOL,
        "sasl_mechanism": kafka_settings.KAFKA_SASL_MECHANISM,
        "sasl_plain_username": kafka_settings.KAFKA_SASL_PLAIN_USERNAME,
        "sasl_plain_password": kafka_settings.KAFKA_SASL_PLAIN_PASSWORD,
        "ssl_context": ssl.create_default_context() if "SSL" in kafka_settings.KAFKA_SECURITY_PROTOCOL else None,
    }
    ws_kwargs = default_consumer_kwargs.copy()
    ws_kwargs["group_id"] = f"ws-{uuid4().hex}"
    ws_messages_consumer = WsMessagesConsumer(
        consumer_class=AIOKafkaConsumer,
        consumer_args=(kafka_settings.WS_SEND_MESSAGES_TOPIC,),
        consumer_kwargs=ws_kwargs,
        logger=logger,
    )
    feed_consumer = FeedConsumer(
        consumer_class=AIOKafkaConsumer,
        consumer_args=(
            kafka_settings.SERVICE_USER_PUBLICATION_TOPIC,
            kafka_settings.SERVICE_USER_EVENT_TOPIC,
        ),
        consumer_kwargs=default_consumer_kwargs,
        logger=logger,
    )
    celebrity_feed_consumer = CelebrityFeedConsumer(
        consumer_class=AIOKafkaConsumer,
        consumer_args=(kafka_settings.SERVICE_FEED_CELEBRITY_TOPIC,),
        consumer_kwargs=default_consumer_kwargs,
        logger=logger,
    )
    processing_event_task = restart_on_exception(
        processing_events_outbox_task,
        run_params={
            "context": context,
            "service_name": app_settings.SERVICE_NAME,
            "topics_map": {EventTypes.SEND_NEW_POST_FOR_FRIENDS: kafka_settings.WS_SEND_MESSAGES_TOPIC},
        },
    )
    await context.start_clients()
    tasks = [
        restart_on_exception(feed_consumer.run),
        restart_on_exception(celebrity_feed_consumer.run),
        restart_on_exception(ws_messages_consumer.run),
        processing_event_task,
    ]
    run_tasks(tasks)
    yield
    await context.stop_clients()
    await shutdown(set(tasks))


app = get_app(app_name=app_settings.SERVICE_NAME, lifespan=lifespan)
