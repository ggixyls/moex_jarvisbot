import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup
from aiokafka import AIOKafkaConsumer

from bot.config import PROJECT_ROOT, Settings
from bot.keyboards.inline import confirmation_keyboard
from bot.services.metrics import response_latency_seconds
from bot.services.request_tracker import RequestTracker
from bot.services.schema_validator import SchemaValidator
from bot.utils.markdown import escape_markdown_v2
from bot.utils.masking import mask_sensitive_data

logger = structlog.get_logger(__name__)


class KafkaConsumerService:
    def __init__(
        self,
        settings: Settings,
        bot: Bot,
        tracker: RequestTracker,
    ) -> None:
        self._settings = settings
        self._bot = bot
        self._tracker = tracker
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None
        self._validator = SchemaValidator(
            PROJECT_ROOT / "schemas" / "worker.responses.schema.json"
        )

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._settings.kafka_responses_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            group_id="redops-telegram-bot",
            auto_offset_reset="latest",
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _consume_loop(self) -> None:
        assert self._consumer is not None
        try:
            async for record in self._consumer:
                try:
                    await self._handle_message(record.value)
                except Exception:
                    logger.exception("response_processing_failed", payload=record.value)
        except asyncio.CancelledError:
            return

    async def _handle_message(self, message: dict[str, Any]) -> None:
        self._validator.validate(message)
        request_id = UUID(message["request_id"])
        tracked = self._tracker.get(request_id)
        if tracked is None:
            logger.warning("orphan_response", request_id=str(request_id))
            return

        latency = (datetime.now(timezone.utc) - tracked.created_at).total_seconds()
        response_latency_seconds.observe(latency)

        status = message["status"]
        chat_id = tracked.chat_id
        logger.info(
            "worker_response_received",
            request_id=str(request_id),
            status=status,
            latency=latency,
        )

        if status == "requires_confirmation":
            self._tracker.await_confirmation(request_id)
            await self._send_confirmation(chat_id, message)
            return

        self._tracker.resolve(request_id)
        text = self._format_response(message)
        await self._bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)

    async def _send_confirmation(self, chat_id: int, message: dict[str, Any]) -> None:
        confirmation_data = message.get("confirmation_data") or {}
        plan = confirmation_data.get("plan", "План действий не получен")
        masked = mask_sensitive_data(confirmation_data)
        details = json.dumps(masked, ensure_ascii=False, indent=2)
        text = (
            f"*План настройки АРМ \\(dry\\-run\\):*\n"
            f"{escape_markdown_v2(plan)}\n\n"
            f"```\n{escape_markdown_v2(details)}\n```\n\n"
            f"Подтвердите выполнение или отмените операцию\\."
        )
        keyboard: InlineKeyboardMarkup = confirmation_keyboard(message["request_id"])
        await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )

    def _format_response(self, message: dict[str, Any]) -> str:
        status = message["status"]
        if status == "success":
            result = message.get("result") or {}
            masked = mask_sensitive_data(result)
            body = json.dumps(masked, ensure_ascii=False, indent=2)
            return f"*Успешно:*\n```\n{escape_markdown_v2(body)}\n```"

        if status == "error":
            error_text = message.get("error") or "Неизвестная ошибка"
            return f"*Ошибка:*\n{escape_markdown_v2(error_text)}"

        if status == "timeout":
            return (
                "*Превышено время ожидания ответа \\(60 сек\\)\\.*\n"
                "Проверьте статус через /status\\."
            )

        body = json.dumps(mask_sensitive_data(message), ensure_ascii=False, indent=2)
        return f"```\n{escape_markdown_v2(body)}\n```"
