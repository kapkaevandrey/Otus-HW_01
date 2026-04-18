import asyncio
from abc import ABC, abstractmethod
from logging import Logger, getLogger
from typing import Any, TypeVar

from .exceptions import SendMessageToKafkaError


ProducerClass = TypeVar("ProducerClass")


class KafkaProducerAbstract[ProducerClass](ABC):
    """
    Abstract Kafka Producer class for send message
    """

    SEND_WITHOUT_TOPIC_MESSAGE = "Cant send message without topic name"

    def __init__(
        self,
        producer_class: type[ProducerClass],
        kafka_params: dict,
        topic: str | None = None,
        logger: Logger | None = None,
    ):
        self._topic = topic
        self._logger = logger or getLogger(__name__)
        self._kafka_params = kafka_params
        self._started = False
        self._producer_class = producer_class
        self._producer: ProducerClass | None = None

    # --- properties ----------------------------------------------------

    @property
    def started(self):
        return self._started

    @property
    def default_topic(self) -> str | None:
        return self._topic

    @property
    def logger(self) -> Logger:
        return self._logger

    # --- base logic ----------------------------------------------------
    async def start(self):
        """Safe start."""
        if self._started:
            return
        try:
            await asyncio.wait_for(self._start(), timeout=10)
            self._started = True
            self._logger.info(f"{self.__class__.__name__}: Producer started. Topic: {self._topic}")
        except Exception as e:
            self._logger.exception(f"{self.__class__.__name__}: Failed to start producer: {e}")
            await self.safe_cleanup()
            raise

    async def safe_cleanup(self):
        """Полная очистка ссылок и сброс состояния."""
        try:
            await self._cleanup()
        except Exception as e:
            self._logger.debug(f"{self.__class__.__name__}: cleanup failed: {e}")
        finally:
            self._started = False
            self._producer = None

    async def stop(self):
        """Безопасная остановка и очистка памяти."""
        if not self._started:
            await self.safe_cleanup()
            return
        try:
            await asyncio.wait_for(self._stop(), timeout=10)
        except Exception as e:
            self._logger.warning(f"{self.__class__.__name__}: stop() failed: {e}")
        finally:
            await self.safe_cleanup()
            self._logger.info(f"{self.__class__.__name__}: Producer stopped. Topic: {self._topic}")

    def _safe_close_task(self, obj: Any, method: str) -> None:
        close_method = getattr(obj, method, None)
        if callable(close_method):
            try:
                close_method()  # pylint: disable=not-callable
            except Exception as e:
                self._logger.debug(f"{self.__class__.__name__}: sender close failed: {e}")

    async def send_message(
        self,
        key: bytes | str | None,
        value: dict | list,
        topic: str | None = None,
        wait_acc: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        key = key.encode() if isinstance(key, str) else key
        topic = topic or self._topic
        if topic is None:
            raise ValueError("Cant send message without topic name")
        await self.start()
        try:
            await self._send_message(
                topic=topic, key=key, value=value, wait_acc=wait_acc, headers=self._prepare_headers(headers)
            )
            self.logger.info(f"Message sent to topic {topic}")
        except Exception as error:
            self.logger.exception(f"Failed send message to topic {topic}. {error} producer stopped", exc_info=True)
            await self.stop()
            raise SendMessageToKafkaError from error

    @staticmethod
    def _prepare_headers(headers: dict[str, str] | None) -> list[tuple[str, bytes]] | None:
        if not headers:
            return None
        kafka_headers = []
        for key, value in headers.items():
            kafka_headers.append((str(key), str(value).encode()))
        return kafka_headers

    @abstractmethod
    async def _send_message(
        self,
        key: bytes | None,
        value: dict | list,
        topic: str,
        wait_acc: bool,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        pass

    @abstractmethod
    async def _start(self):
        """
        Real start producer operation.
        1. Init producer self._producer = self._producer_class(**kafka_params, **aditional params)
        2. await producer.start()
        """
        pass

    @abstractmethod
    async def _stop(self):
        """
        Real stop producer operation.
        await producer.stop()
        """
        pass

    @abstractmethod
    async def _cleanup(self):
        """
        Real clean producer operation.
        """
        pass
