import asyncio
import logging
import signal
from uuid import UUID

import structlog
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.handlers import build_router
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.input_validation import InputValidationMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.services.kafka_consumer import KafkaConsumerService
from bot.services.kafka_producer import KafkaProducerService
from bot.services.metrics import start_metrics_server
from bot.services.request_tracker import RequestTracker
def setup_logging(level: str) -> None:
    logging.basicConfig(level=level)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
    )


async def on_timeout(bot: Bot, request_id: UUID, chat_id: int) -> None:
    text = (
        "*Превышено время ожидания ответа \\(60 сек\\)\\.*\n"
        "Проверьте статус через /status\\."
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
    structlog.get_logger(__name__).warning("timeout_notified", request_id=str(request_id))


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = structlog.get_logger(__name__)

    start_metrics_server(settings.metrics_port)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())

    tracker = RequestTracker(timeout_seconds=settings.response_timeout_seconds)
    producer = KafkaProducerService(settings)
    consumer = KafkaConsumerService(settings, bot, tracker)

    async def timeout_handler(request_id: UUID, chat_id: int) -> None:
        await on_timeout(bot, request_id, chat_id)

    dispatcher.message.middleware(LoggingMiddleware())
    dispatcher.callback_query.middleware(LoggingMiddleware())
    dispatcher.message.middleware(AuthMiddleware(settings))
    dispatcher.callback_query.middleware(AuthMiddleware(settings))
    dispatcher.message.middleware(RateLimitMiddleware(settings))
    dispatcher.message.middleware(InputValidationMiddleware(settings))

    dispatcher.include_router(build_router())

    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    await producer.start()
    await consumer.start()
    logger.info("bot_started")

    polling_task = asyncio.create_task(
        dispatcher.start_polling(
            bot,
            producer=producer,
            tracker=tracker,
            on_timeout=timeout_handler,
        )
    )

    await stop_event.wait()

    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    await consumer.stop()
    await producer.stop()
    await bot.session.close()
    logger.info("bot_stopped")


if __name__ == "__main__":
    asyncio.run(main())
