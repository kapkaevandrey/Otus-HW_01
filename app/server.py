import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apps.api import main_router
from app.config import app_settings
from app.core.containers import get_context


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
    await context.start_clients()
    yield
    await context.stop_clients()


app = get_app(app_name=app_settings.SERVICE_NAME, lifespan=lifespan)
