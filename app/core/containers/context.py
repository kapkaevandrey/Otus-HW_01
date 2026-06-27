import ssl
from logging import Logger, getLogger

from aiokafka import AIOKafkaProducer

from app.config import chat_settings, db_settings, kafka_settings, redis_settings
from app.core.clients import ChatServiceClient, KafkaProducerAIO, RedisClient, SQLAlchemyAsyncPgClient
from app.core.clients.ws import SocketConnectionManager
from app.core.repositories import UnitOfWork


class Context:
    def __init__(
        self,
        kafka_producer: KafkaProducerAIO,
        db_client: SQLAlchemyAsyncPgClient,
        redis_client: RedisClient,
        socket_manager: SocketConnectionManager,
        chat_service_client: ChatServiceClient,
        logger: Logger | None = None,
    ) -> None:
        self._db_client = db_client
        self._socket_manager = socket_manager
        self._kafka_producer = kafka_producer
        self._redis_client = redis_client
        self._chat_service_client = chat_service_client
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
    def socket_manager(self) -> SocketConnectionManager:
        return self._socket_manager

    @property
    def chat_service_client(self) -> ChatServiceClient:
        return self._chat_service_client

    @property
    def uow(self):
        return UnitOfWork(db_client=self._db_client)

    @property
    def logger(self) -> Logger:
        return self._logger

    async def start_clients(self):
        """Start all clients if that need"""
        await self._db_client.start_client()
        await self.socket_manager.start()
        await self._kafka_producer.start()

    async def stop_clients(self):
        """Stop all clients if that need"""
        await self.db_client.stop_client()
        await self._kafka_producer.stop()
        await self.socket_manager.stop()
        await self._chat_service_client.aclose()


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
    socket_manager=SocketConnectionManager(),
    redis_client=RedisClient.from_settings(redis_settings),
    chat_service_client=ChatServiceClient.from_settings(chat_settings),
    logger=getLogger(__name__),
)


def get_context() -> Context:
    return context
