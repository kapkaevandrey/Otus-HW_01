import asyncio
import json

from aiokafka import AIOKafkaProducer

from .base import KafkaProducerAbstract


class KafkaProducerAIO(KafkaProducerAbstract[AIOKafkaProducer]):
    async def _start(self):
        self._producer = self._producer_class(
            value_serializer=lambda x: json.dumps(x, ensure_ascii=False).encode("utf-8"), **self._kafka_params
        )
        await self._producer.start()

    async def _stop(self):
        try:
            await self._producer.stop()
        except Exception as e:
            self.logger.warning(f"Kafka producer stop failed: {e}")

    async def _cleanup(self):
        if self._producer:
            if sender := getattr(self._producer, "_sender", None):
                self._safe_close_task(sender, "close")
                self._producer._sender = None
            if hasattr(self._producer, "_client"):
                self._producer._client = None
        await asyncio.sleep(0)  # switch context for waiting task finished

    async def _send_message(
        self,
        key: bytes | None,
        value: dict | list,
        topic: str,
        wait_acc: bool,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        if not self._producer:
            raise ValueError("Producer not started")
        if wait_acc:
            await self._producer.send_and_wait(topic=topic, key=key, value=value, headers=headers)
        else:
            await self._producer.send(topic=topic, key=key, value=value, headers=headers)
