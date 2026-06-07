from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers.common import submit_request
from bot.services.kafka_producer import KafkaProducerService
from bot.services.request_tracker import RequestTracker
from bot.utils.markdown import escape_markdown_v2

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Добро пожаловать в RedOps Telegram Bot\\.\n\n"
        "Доступные команды:\n"
        "/diagnose \\- диагностика аутентификации\n"
        "/setup \\- настройка АРМ\n"
        "/status \\- статус запросов\n"
        "/help \\- справка"
    )
    await message.answer(text, parse_mode="MarkdownV2")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "*Справка RedOps Bot*\n\n"
        "*Диагностика* \\(/diagnose\\): проверка sssd/realm, связи с AD, "
        "разделение проблем аутентификации и авторизации\\.\n"
        "*Настройка АРМ* \\(/setup\\): сбор сетевых параметров, dry\\-run и "
        "подтверждение перед реальным выполнением\\.\n"
        "*Статус* \\(/status\\): проверка активных запросов\\.\n\n"
        "Также можно описать проблему естественным языком, например:\n"
        f"{escape_markdown_v2('Пользователь не заходит по SSH, Permission denied')}"
    )
    await message.answer(text, parse_mode="MarkdownV2")


@router.message(Command("status"))
async def cmd_status(
    message: Message,
    producer: KafkaProducerService,
    tracker: RequestTracker,
    on_timeout,
) -> None:
    pending = tracker.pending_for_user(message.from_user.id)
    if pending:
        lines = [f"• `{item.request_id}`" for item in pending]
        local_status = "Активные запросы:\n" + "\n".join(lines)
        await message.answer(local_status, parse_mode="MarkdownV2")

    await submit_request(
        message,
        producer=producer,
        tracker=tracker,
        intent="status",
        payload={},
        on_timeout=on_timeout,
    )
