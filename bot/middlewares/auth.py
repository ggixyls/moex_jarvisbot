from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.config import Settings

logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._whitelist = set(settings.whitelist_user_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        if user.id not in self._whitelist:
            logger.warning("access_denied", user_id=user.id)
            if isinstance(event, Message):
                await event.answer(
                    "Доступ запрещён. Обратитесь к администратору для добавления в WhiteList."
                )
            return None

        return await handler(event, data)
