from uuid import UUID

from aiogram.enums import ChatAction
from aiogram.types import Message

from bot.services.kafka_producer import KafkaProducerService
from bot.services.request_tracker import RequestTracker


async def submit_request(
    message: Message,
    *,
    producer: KafkaProducerService,
    tracker: RequestTracker,
    intent: str,
    payload: dict,
    on_timeout,
    request_id: UUID | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> UUID:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer("Запрос принят. Идет обработка...", parse_mode=None)

    if user_id is None:
        user = message.from_user
        assert user is not None
        user_id = user.id
        username = user.username

    published_id = await producer.publish(
        user_id=user_id,
        username=username,
        intent=intent,
        payload=payload,
        request_id=request_id,
    )
    tracker.register(
        request_id=published_id,
        chat_id=message.chat.id,
        user_id=user_id,
        payload=payload,
        on_timeout=on_timeout,
    )
    return published_id
