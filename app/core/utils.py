import asyncio
import datetime as dt
from collections.abc import Awaitable, Callable, Coroutine
from logging import getLogger


logger = getLogger(__name__)


def utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


async def restart_on_exception(
    task: Callable[..., Awaitable], run_params: dict | None = None, backoff_in_seconds: int = 2
) -> None:
    run_params = run_params or {}
    while True:
        try:
            await task(**run_params)
        except asyncio.CancelledError:
            # do not restart cancelled tasks
            break
        except Exception:
            logger.exception("Error in task %s", task.__name__)
            await asyncio.sleep(backoff_in_seconds)


def run_tasks(tasks: list[Coroutine]) -> None:
    loop = asyncio.get_event_loop()

    for task in tasks:
        asyncio.ensure_future(task, loop=loop)


async def shutdown(to_cancel: set[Coroutine]) -> None:
    """Call `cancel()` on received coroutines' tasks.

    :param to_cancel: list of coroutines to cancel
    """
    logger.info("shutdown is started")
    tasks = []
    for task in asyncio.all_tasks():
        if task.get_coro() in to_cancel and not task.cancelled():
            task.cancel()
            tasks.append(task)
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("shutdown is ended")
