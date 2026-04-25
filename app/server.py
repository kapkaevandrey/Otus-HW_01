import asyncio
import logging
import ssl
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apps.api import main_router
from app.apps.consumers import CacheFeedConsumer
from app.config import app_settings, kafka_settings
from app.core.containers import get_context
from app.core.utils import restart_on_exception, run_tasks, shutdown


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


def get_app(app_name: str, lifespan: Callable) -> FastAPI:
    application = FastAPI(
        title=app_name,
        root_path=app_settings.ROOT_PATH,
        debug=app_settings.DEBUG,
        event_manager_queue=asyncio.Queue(),
        statistic_queue=asyncio.Queue(),
        lifespan=lifespan,
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
    tasks = []
    feed_cache_consumer = CacheFeedConsumer(
        consumer_class=AIOKafkaConsumer,
        consumer_args=(
            kafka_settings.SERVICE_USER_PUBLICATION_TOPIC,
            kafka_settings.SERVICE_USER_EVENT_TOPIC,
        ),
        consumer_kwargs=default_consumer_kwargs,
        logger=logger,
    )
    tasks.append(restart_on_exception(feed_cache_consumer.run))
    await context.start_clients()
    run_tasks(tasks)
    yield
    await context.stop_clients()
    await shutdown(set(tasks))


app = get_app(app_name=app_settings.SERVICE_NAME, lifespan=lifespan)
