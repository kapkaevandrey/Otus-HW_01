import ssl
from logging import Logger, getLogger

from aiokafka import AIOKafkaProducer

from app.config import db_settings, kafka_settings, redis_settings
from app.core.clients import KafkaProducerAIO, RedisClient, SQLAlchemyAsyncPgClient
from app.core.repositories import UnitOfWork


class Context:
    def __init__(
        self,
        kafka_producer: KafkaProducerAIO,
        db_client: SQLAlchemyAsyncPgClient,
        redis_client: RedisClient,
        logger: Logger | None = None,
    ) -> None:
        self._db_client = db_client
        self._kafka_producer = kafka_producer
        self._redis_client = redis_client
        self._logger = logger or getLogger(__name__)

    @property
    def db_client(self) -> SQLAlchemyAsyncPgClient:
        return self._db_client

    @property
    def kafka_producer(self) -> KafkaProducerAIO:
        return self._kafka_producer

    @property
    def redis_client(self) -> RedisClient:
        return self._redis_client

    @property
    def uow(self):
        return UnitOfWork(db_client=self._db_client)

    @property
    def logger(self) -> Logger:
        return self._logger

    async def start_clients(self):
        """Start all clients if that need"""
        await self._db_client.start_client()
        await self._kafka_producer.start()

    async def stop_clients(self):
        """Stop all clients if that need"""
        await self.db_client.stop_client()
        await self._kafka_producer.stop()


context = Context(
    db_client=SQLAlchemyAsyncPgClient.from_settings(db_settings),
    kafka_producer=KafkaProducerAIO(
        kafka_params={
            "bootstrap_servers": kafka_settings.KAFKA_BROKERS,
            "security_protocol": kafka_settings.KAFKA_SECURITY_PROTOCOL,
            "sasl_mechanism": kafka_settings.KAFKA_SASL_MECHANISM,
            "sasl_plain_username": kafka_settings.KAFKA_SASL_PLAIN_USERNAME,
            "sasl_plain_password": kafka_settings.KAFKA_SASL_PLAIN_PASSWORD,
            "ssl_context": ssl.create_default_context() if "SSL" in kafka_settings.KAFKA_SECURITY_PROTOCOL else None,
        },
        producer_class=AIOKafkaProducer,
        topic=None,
    ),
    redis_client=RedisClient.from_settings(redis_settings),
    logger=getLogger(__name__),
)


def get_context() -> Context:
    return context
