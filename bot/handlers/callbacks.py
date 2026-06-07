from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.common import submit_request
from bot.services.kafka_producer import KafkaProducerService
from bot.services.request_tracker import RequestTracker

router = Router()


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_execution(
    callback: CallbackQuery,
    producer: KafkaProducerService,
    tracker: RequestTracker,
    on_timeout,
) -> None:
    request_id = UUID(callback.data.split(":", 1)[1])
    tracked = tracker.get(request_id)
    if tracked is None:
        await callback.answer("Запрос устарел или уже обработан.", show_alert=True)
        return

    payload = dict(tracked.payload)
    payload["dry_run"] = False
    tracker.resolve(request_id)

    if callback.message is None:
        await callback.answer()
        return

    await callback.answer("Запуск реального выполнения...")
    await submit_request(
        callback.message,
        producer=producer,
        tracker=tracker,
        intent="setup_workstation",
        payload=payload,
        on_timeout=on_timeout,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
    )


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_execution(callback: CallbackQuery, tracker: RequestTracker) -> None:
    request_id = UUID(callback.data.split(":", 1)[1])
    tracker.resolve(request_id)
    await callback.answer("Операция отменена.")
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Настройка АРМ отменена пользователем.")
