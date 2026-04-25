import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from aiokafka import AIOKafkaConsumer, ConsumerRecord
from pydantic import PositiveInt

from .exceptions import ImproperlyConfiguredError, RetriesExceededError


class BaseKafkaConsumer:
    def __init__(
        self,
        consumer_class: type[AIOKafkaConsumer],
        consumer_args: tuple,
        consumer_kwargs: dict,
        process_retries: PositiveInt = 1,
        logger: logging.Logger | None = None,
    ):
        """Async kafka consumer. Implements automatic start/stop operations.
        Provides retries if process_message operation ended up with failure.

        Args:
            consumer_class (AIOKafkaConsumer, type): Kafka consumer class
            consumer_args (Tuple): positional arguments for kafka consumer to initialize
            consumer_kwargs (Dict): named arguments for kafka consumer to inisialize
            process_retries (int, optional): number attempts to process incoming message.
                 After provided number of failures `RetriesExceeded` exception will be raised. Defaults to 1.
            logger (logging.Logger, optional): Logger instance. Defaults to default logger.
        Raises:
            ImproperlyConfiguratedError: raises if process_retries  is not positive integer
        """
        if not (isinstance(process_retries, int) and process_retries > 0):
            raise ImproperlyConfiguredError("'process_retries' must be positive integer")

        self.consumer_class = consumer_class
        self.consumer_args = consumer_args
        self.consumer_kwargs = consumer_kwargs
        self.consumer = None
        self._process_retries = process_retries

        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger

    def consumer_is_started(self) -> bool:
        """Function to check if `start` method of aiokafka.KafkaConsumer was
        called.

        Returns:
            bool: True if consumer is started
        """
        return self.consumer is not None

    async def start(self):
        """Starts consumer.

        Creates consumer instance if it does not exist. Stops current
        consumer if exists
        """
        if self.consumer:
            await self.stop()
        self.consumer = self.consumer_class(*self.consumer_args, **self.consumer_kwargs)
        await self.consumer.start()

    async def stop(self):
        """Stops consumer."""
        if not self.consumer:
            return
        await self.consumer.stop()
        self.consumer = None

    async def run(self, once: bool = False) -> None:
        """Runs a loop of reading and processing messages from kafka through
        the consumer specified during initialization.

        Args:
            once (bool, optional): If true, loop will be broken after first message read. Defaults to False.

        Raises:
            RetriesExceeded: raises if number of attempts to process message exceeded
                  process_retries parameter specified during initialization
        """
        self.logger.info(f"{self.__class__.__name__}: Consumer started")
        if not self.consumer_is_started():
            await self.start()
        try:
            await self._read_messages(once=once)
        finally:
            await self.stop()
            self.logger.info(f"{self.__class__.__name__}: Consumer stopped")

    async def _read_messages(self, once: bool = False) -> None:
        async for msg in self.consumer:  # type: ignore
            async with self.context_manager() as context:
                self.logger.debug(f"{self.__class__.__name__}: Reading message: {msg}")
                for _ in range(self._process_retries):
                    try:
                        await self.process_message(msg, context)
                        break
                    except Exception:
                        self.logger.exception(f"{self.__class__.__name__}: Error while processing message {msg.value}")
                else:
                    raise RetriesExceededError(
                        f"{self.__class__.__name__}: Number of retires exceeded ({self._process_retries})"
                    )
                await self.consumer.commit()  # type: ignore
                if once:
                    break

    async def process_message(self, message: ConsumerRecord, context: Any = None) -> None:
        """Processes an incoming message from kafka. Must be overriden to
        consumer work properly.

        Args:
            message (kafka.protocol.message.Message): message read from kafka
            context (Any, optional): context metadata provided by `self.context_manager` function. Defaults to None.

        Raises:
            NotImplementedError: generally raises NotImplementedError. This method must be overloaded in child classes
        """
        raise NotImplementedError

    @asynccontextmanager
    async def context_manager(self) -> AsyncGenerator:
        """Context manager to wrap process messages operations. Needs to
        implement such functions as action collector, sqlalchemy AsyncSession,
        etc.

        Returns:
            AsyncGenerator: generated metadata
        """
        yield
