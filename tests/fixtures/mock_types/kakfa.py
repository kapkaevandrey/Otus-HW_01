from collections import defaultdict, deque

from app.core.clients.kafka import KafkaProducerAbstract


class MockAiokafkaProducerClass:
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass


class MockKafkaProducer(KafkaProducerAbstract[MockAiokafkaProducerClass]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = defaultdict(deque)

    async def _start(self):
        self._producer = self._producer_class()
        await self._producer.start()

    async def _stop(self):
        if self._producer:
            await self._producer.stop()

    async def _cleanup(self):
        pass

    async def _send_message(
        self,
        key: bytes | None,
        value: dict | list,
        topic: str,
        wait_acc: bool,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        self.messages[topic].append((key, value))
