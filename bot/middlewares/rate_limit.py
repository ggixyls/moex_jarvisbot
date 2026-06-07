from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.config import Settings


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._limit = settings.rate_limit_per_minute
        self._requests: dict[int, deque[datetime]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        user_id = event.from_user.id
        queue = self._requests[user_id]

        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= self._limit:
            await event.answer("Превышен лимит запросов: не более 10 в минуту.")
            return None

        queue.append(now)
        return await handler(event, data)
