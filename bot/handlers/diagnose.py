import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.handlers.common import submit_request
from bot.services.kafka_producer import KafkaProducerService
from bot.services.request_tracker import RequestTracker
from bot.utils.validators import validate_domain

router = Router()

_DIAGNOSE_PATTERN = re.compile(
    r"(не\s+заходит|permission\s+denied|ssh|аутентификац|авторизац|sssd|kerberos|pam)",
    re.IGNORECASE,
)


class DiagnoseStates(StatesGroup):
    waiting_username = State()
    waiting_domain = State()


@router.message(Command("diagnose"))
async def cmd_diagnose(message: Message, state: FSMContext) -> None:
    await state.set_state(DiagnoseStates.waiting_username)
    await message.answer("Введите имя пользователя (username):")


@router.message(F.text.regexp(_DIAGNOSE_PATTERN))
async def natural_diagnose(message: Message, state: FSMContext) -> None:
    if message.text and message.text.startswith("/"):
        return
    await state.update_data(problem_description=message.text)
    await state.set_state(DiagnoseStates.waiting_username)
    await message.answer("Введите имя пользователя (username):")


@router.message(StateFilter(DiagnoseStates.waiting_username))
async def process_username(message: Message, state: FSMContext) -> None:
    username = (message.text or "").strip()
    if not username:
        await message.answer("Имя пользователя не может быть пустым.")
        return
    await state.update_data(username=username)
    await state.set_state(DiagnoseStates.waiting_domain)
    await message.answer("Введите домен (domain):")


@router.message(StateFilter(DiagnoseStates.waiting_domain))
async def process_domain(
    message: Message,
    state: FSMContext,
    producer: KafkaProducerService,
    tracker: RequestTracker,
    on_timeout,
) -> None:
    domain = (message.text or "").strip()
    if not validate_domain(domain):
        await message.answer("Некорректный домен. Пример: corp.local")
        return

    data = await state.get_data()
    payload = {
        "username": data["username"],
        "domain": domain,
    }
    if "problem_description" in data:
        payload["problem_description"] = data["problem_description"]

    await submit_request(
        message,
        producer=producer,
        tracker=tracker,
        intent="diagnose_auth",
        payload=payload,
        on_timeout=on_timeout,
    )
    await state.clear()
