import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from bot.config import PROJECT_ROOT, Settings
from bot.services.metrics import kafka_publish_errors_total
from bot.services.schema_validator import SchemaValidator

logger = structlog.get_logger(__name__)


class KafkaProducerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None
        self._validator = SchemaValidator(PROJECT_ROOT / "schemas" / "tg.requests.schema.json")

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        await self._retry(self._producer.start)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(
        self,
        *,
        user_id: int,
        username: str | None,
        intent: str,
        payload: dict[str, Any],
        request_id: UUID | None = None,
    ) -> UUID:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")

        message_id = request_id or uuid4()
        message = {
            "request_id": str(message_id),
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "payload": payload,
        }
        self._validator.validate(message)

        try:
            await self._retry(
                self._producer.send_and_wait,
                self._settings.kafka_requests_topic,
                message,
            )
        except KafkaError:
            kafka_publish_errors_total.inc()
            raise

        logger.info(
            "kafka_request_published",
            request_id=str(message_id),
            intent=intent,
            user_id=user_id,
        )
        return message_id

    async def _retry(self, operation, *args, **kwargs) -> Any:
        delay = 1.0
        last_error: Exception | None = None
        for _ in range(5):
            try:
                return await operation(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                logger.warning("kafka_retry", error=str(exc), delay=delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Kafka operation failed")
