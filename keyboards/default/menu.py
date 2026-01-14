from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.localization import get_text

def get_language_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_contact_keyboard(lang: str):
    text = get_text("contact_button", lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text, request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_main_menu_keyboard(lang: str):
    btn_order = KeyboardButton(text=get_text("btn_order", lang))
    btn_history = KeyboardButton(text=get_text("btn_history", lang))
    btn_settings = KeyboardButton(text=get_text("btn_settings", lang))
    btn_contact = KeyboardButton(text=get_text("btn_contact", lang))
    btn_comment = KeyboardButton(text=get_text("btn_comment", lang))

    return ReplyKeyboardMarkup(
        keyboard=[
            [btn_order],
            [btn_history, btn_settings],
            [btn_contact, btn_comment]
        ],
        resize_keyboard=True
    )
