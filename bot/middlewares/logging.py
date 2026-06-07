from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.services.metrics import messages_received_total
from bot.utils.masking import mask_sensitive_data

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_type = type(event).__name__
        payload: dict[str, Any] = {"event_type": event_type}

        if isinstance(event, Message):
            messages_received_total.labels(handler="message").inc()
            payload.update(
                {
                    "user_id": event.from_user.id if event.from_user else None,
                    "chat_id": event.chat.id,
                    "text": event.text,
                }
            )
        elif isinstance(event, CallbackQuery):
            messages_received_total.labels(handler="callback").inc()
            payload.update(
                {
                    "user_id": event.from_user.id if event.from_user else None,
                    "data": event.data,
                }
            )

        logger.info("incoming_event", **mask_sensitive_data(payload))
        result = await handler(event, data)
        logger.info("outgoing_event", event_type=event_type, handled=result is not None)
        return result
