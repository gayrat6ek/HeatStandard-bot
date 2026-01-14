from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from states.registration import RegisterState, OrderState, MenuState
from keyboards.default.menu import get_language_keyboard, get_contact_keyboard, get_main_menu_keyboard
from utils.api import api_client
from utils.localization import get_text, LANG_MAP

router = Router()


async def initialize_user(message: types.Message, state: FSMContext):
    """Common initialization logic - used by both /start and catch-all handler."""
    telegram_id = str(message.from_user.id)
    
    # Check if user exists via login check
    user_data = await api_client.login_user(telegram_id)
    
    if "access_token" in user_data:
        # User exists and is active
        user = user_data.get("user", {})
        lang = user.get("current_lang", "ru")
        await state.update_data(lang=lang, token=user_data["access_token"])
        
        welcome_msg = get_text("welcome_back", lang).replace("{name}", user.get('full_name', ''))
        await message.answer(welcome_msg, reply_markup=get_main_menu_keyboard(lang))
        return True

    # If login failed, check if user exists but inactive
    existing_user = await api_client.get_user(telegram_id)
    
    if existing_user and existing_user.get("id"):
        if not existing_user.get("is_active"):
            lang = existing_user.get("current_lang", "ru")
            await message.answer(get_text("already_registered_wait", lang))
            return True
    
    # Not registered - start registration
    await message.answer(get_text("welcome", "ru"), reply_markup=get_language_keyboard())
    await state.set_state(RegisterState.language)
    return True


@router.message(CommandStart())
async def bot_start(message: types.Message, state: FSMContext):
    await initialize_user(message, state)


@router.message(RegisterState.language)
async def language_selected(message: types.Message, state: FSMContext):
    text = message.text
    if text not in LANG_MAP:
        await message.answer("Please select a button / Пожалуйста, выберите кнопку")
        return
    
    lang_code = LANG_MAP[text]
    await state.update_data(lang=lang_code)
    
    await message.answer(get_text("share_contact", lang_code), reply_markup=get_contact_keyboard(lang_code))
    await state.set_state(RegisterState.phone)


@router.message(RegisterState.phone, F.contact)
async def contact_shared(message: types.Message, state: FSMContext):
    contact = message.contact
    if not contact:
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Register user
    res = await api_client.register_user(
        telegram_id=str(message.from_user.id),
        phone_number=contact.phone_number,
        full_name=message.from_user.full_name or "Unknown",
        language=lang
    )
    
    if "error" in res:
        await message.answer(f"Error: {res['error']}")
        return

    await message.answer(get_text("registered_wait", lang), reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.message(F.text)
async def catch_all_text_handler(message: types.Message, state: FSMContext):
    """Catch-all handler for users who haven't started the bot.
    
    If user has no state (never pressed /start), initialize them.
    This ensures the bot works even after a restart without requiring /start.
    """
    current_state = await state.get_state()
    data = await state.get_data()
    
    # If user has no state and no data, initialize them
    if current_state is None and not data.get("lang"):
        await initialize_user(message, state)
