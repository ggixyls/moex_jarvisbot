from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.config import Settings


class InputValidationMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._max_length = settings.max_input_length

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and len(event.text) > self._max_length:
            await event.answer(
                f"Слишком длинное сообщение. Максимум {self._max_length} символов."
            )
            return None
        return await handler(event, data)
