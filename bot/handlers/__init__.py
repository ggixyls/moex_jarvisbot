from aiogram import Router

from bot.handlers import callbacks, commands, diagnose, setup


def build_router() -> Router:
    router = Router()
    router.include_router(commands.router)
    router.include_router(diagnose.router)
    router.include_router(setup.router)
    router.include_router(callbacks.router)
    return router
