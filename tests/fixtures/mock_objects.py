from collections.abc import Generator
from typing import Any

import pytest

from .mock_types import MockAiokafkaProducerClass, MockKafkaProducer


@pytest.fixture
def kafka_producer_mock_client() -> Generator[MockKafkaProducer, Any]:
    client = MockKafkaProducer(topic="kopic", kafka_params={}, producer_class=MockAiokafkaProducerClass)
    yield client
    client.messages.clear()
