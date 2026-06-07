import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.handlers.common import submit_request
from bot.services.kafka_producer import KafkaProducerService
from bot.services.request_tracker import RequestTracker
from bot.utils.validators import validate_domain, validate_hostname, validate_ip

router = Router()

_SETUP_PATTERN = re.compile(
    r"(настро(й|ить)|арм|workstation|hostname|сетев|ip|dns|домен)",
    re.IGNORECASE,
)


class SetupStates(StatesGroup):
    waiting_hostname = State()
    waiting_ip = State()
    waiting_netmask = State()
    waiting_gateway = State()
    waiting_dns = State()
    waiting_domain = State()
    waiting_domain_user = State()
    waiting_admin_pass = State()


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext) -> None:
    await state.set_state(SetupStates.waiting_hostname)
    await message.answer("Введите hostname:")


@router.message(F.text.regexp(_SETUP_PATTERN))
async def natural_setup(message: Message, state: FSMContext) -> None:
    if message.text and message.text.startswith("/"):
        return
    await state.set_state(SetupStates.waiting_hostname)
    await message.answer("Введите hostname:")


@router.message(StateFilter(SetupStates.waiting_hostname))
async def process_hostname(message: Message, state: FSMContext) -> None:
    hostname = (message.text or "").strip()
    if not validate_hostname(hostname):
        await message.answer("Некорректный hostname.")
        return
    await state.update_data(hostname=hostname)
    await state.set_state(SetupStates.waiting_ip)
    await message.answer("Введите статический IP:")


@router.message(StateFilter(SetupStates.waiting_ip))
async def process_ip(message: Message, state: FSMContext) -> None:
    ip_address = (message.text or "").strip()
    if not validate_ip(ip_address):
        await message.answer("Некорректный IP-адрес.")
        return
    await state.update_data(ip=ip_address)
    await state.set_state(SetupStates.waiting_netmask)
    await message.answer("Введите маску подсети:")


@router.message(StateFilter(SetupStates.waiting_netmask))
async def process_netmask(message: Message, state: FSMContext) -> None:
    netmask = (message.text or "").strip()
    if not validate_ip(netmask):
        await message.answer("Некорректная маска подсети.")
        return
    await state.update_data(netmask=netmask)
    await state.set_state(SetupStates.waiting_gateway)
    await message.answer("Введите шлюз (gateway):")


@router.message(StateFilter(SetupStates.waiting_gateway))
async def process_gateway(message: Message, state: FSMContext) -> None:
    gateway = (message.text or "").strip()
    if not validate_ip(gateway):
        await message.answer("Некорректный шлюз.")
        return
    await state.update_data(gateway=gateway)
    await state.set_state(SetupStates.waiting_dns)
    await message.answer("Введите DNS-сервер:")


@router.message(StateFilter(SetupStates.waiting_dns))
async def process_dns(message: Message, state: FSMContext) -> None:
    dns = (message.text or "").strip()
    if not validate_ip(dns):
        await message.answer("Некорректный DNS.")
        return
    await state.update_data(dns=dns)
    await state.set_state(SetupStates.waiting_domain)
    await message.answer("Введите домен:")


@router.message(StateFilter(SetupStates.waiting_domain))
async def process_domain(message: Message, state: FSMContext) -> None:
    domain = (message.text or "").strip()
    if not validate_domain(domain):
        await message.answer("Некорректный домен. Пример: corp.local")
        return
    await state.update_data(domain=domain)
    await state.set_state(SetupStates.waiting_domain_user)
    await message.answer("Введите учётные данные для входа в домен (username):")


@router.message(StateFilter(SetupStates.waiting_domain_user))
async def process_domain_user(message: Message, state: FSMContext) -> None:
    domain_user = (message.text or "").strip()
    if not domain_user:
        await message.answer("Имя пользователя не может быть пустым.")
        return
    await state.update_data(domain_user=domain_user)
    await state.set_state(SetupStates.waiting_admin_pass)
    await message.answer("Введите пароль (admin_pass):")


@router.message(StateFilter(SetupStates.waiting_admin_pass))
async def process_admin_pass(
    message: Message,
    state: FSMContext,
    producer: KafkaProducerService,
    tracker: RequestTracker,
    on_timeout,
) -> None:
    admin_pass = (message.text or "").strip()
    if not admin_pass:
        await message.answer("Пароль не может быть пустым.")
        return

    data = await state.get_data()
    payload = {
        "hostname": data["hostname"],
        "ip": data["ip"],
        "netmask": data["netmask"],
        "gateway": data["gateway"],
        "dns": data["dns"],
        "domain": data["domain"],
        "domain_user": data["domain_user"],
        "admin_pass": admin_pass,
        "dry_run": True,
    }

    await submit_request(
        message,
        producer=producer,
        tracker=tracker,
        intent="setup_workstation",
        payload=payload,
        on_timeout=on_timeout,
    )
    await state.clear()
