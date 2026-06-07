import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

TimeoutCallback = Callable[[UUID, int], Awaitable[None]]


@dataclass
class TrackedRequest:
    request_id: UUID
    chat_id: int
    user_id: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)


class RequestTracker:
    def __init__(self, timeout_seconds: int) -> None:
        self._timeout_seconds = timeout_seconds
        self._requests: dict[UUID, TrackedRequest] = {}
        self._timers: dict[UUID, asyncio.Task[None]] = {}

    def register(
        self,
        request_id: UUID,
        chat_id: int,
        user_id: int,
        payload: dict[str, Any] | None = None,
        on_timeout: TimeoutCallback | None = None,
    ) -> None:
        self._requests[request_id] = TrackedRequest(
            request_id=request_id,
            chat_id=chat_id,
            user_id=user_id,
            payload=payload or {},
        )
        if on_timeout is not None:
            self._timers[request_id] = asyncio.create_task(
                self._watch_timeout(request_id, on_timeout)
            )

    def resolve(self, request_id: UUID) -> TrackedRequest | None:
        tracked = self._requests.pop(request_id, None)
        self._cancel_timer(request_id)
        return tracked

    def await_confirmation(self, request_id: UUID) -> None:
        self._cancel_timer(request_id)

    def get(self, request_id: UUID) -> TrackedRequest | None:
        return self._requests.get(request_id)

    def _cancel_timer(self, request_id: UUID) -> None:
        timer = self._timers.pop(request_id, None)
        if timer is not None:
            timer.cancel()

    def pending_for_user(self, user_id: int) -> list[TrackedRequest]:
        return [item for item in self._requests.values() if item.user_id == user_id]

    async def _watch_timeout(self, request_id: UUID, on_timeout: TimeoutCallback) -> None:
        try:
            await asyncio.sleep(self._timeout_seconds)
            tracked = self.resolve(request_id)
            if tracked is not None:
                logger.warning("request_timeout", request_id=str(request_id))
                await on_timeout(request_id, tracked.chat_id)
        except asyncio.CancelledError:
            return
