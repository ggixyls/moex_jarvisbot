from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить выполнение",
                    callback_data=f"confirm:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"cancel:{request_id}",
                ),
            ]
        ]
    )
