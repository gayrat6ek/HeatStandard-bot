from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from utils.localization import get_text, LANG_MAP, format_price
from keyboards.default.menu import get_language_keyboard, get_main_menu_keyboard
from utils.api import api_client
from states.registration import RegisterState

router = Router()
router.message.filter(F.chat.type == "private")

@router.message(F.text == "📱 Kontaktni yuborish")
@router.message(F.text == "📱 Отправить контакт") 
@router.message(F.text == "📱 Share Contact")
async def share_contact_handler(message: types.Message):
    # This is handled in start.py usually but if it's main menu... 
    # Wait, the main menu has "Contact Us" (Biz bilan aloqa)
    pass

@router.message(lambda msg: msg.text in ["📞 Biz bilan aloqa", "📞 Связаться с нами", "📞 Contact Us"])
async def contact_us(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Static contact info for now
    contact_text = {
        "uz": "Biz bilan bog'lanish:\nTel: +998 90 123 45 67\nTelegram: @admin",
        "ru": "Наши контакты:\nТел: +998 90 123 45 67\nTelegram: @admin",
        "en": "Contact us:\nPhone: +998 90 123 45 67\nTelegram: @admin"
    }
    await message.answer(contact_text.get(lang, contact_text["ru"]))

@router.message(lambda msg: msg.text in ["⚙️ Sozlamalar", "⚙️ Настройки", "⚙️ Settings"])
async def settings_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    await message.answer(get_text("welcome", lang), reply_markup=get_language_keyboard())
    # Note: We are reusing the language keyboard. 
    # We might need a state if we want to update language and return to menu immediately.
    # But start.py handles language selection for registration. 
    # We should add a handler for language selection in general context or reuse start logic if possible.
    # For now, let's just let them select language and it will trigger the start.py handler? 
    # No, start.py checks RegisterState.language.
    
    # Let's import RegisterState and set it? Or create a SettingsState?
    from states.registration import MenuState
    await state.set_state(MenuState.language)

@router.message(lambda msg: msg.text in ["✍️ Izoh qoldirish", "✍️ Оставить комментарий", "✍️ Leave a Comment"])
async def comment_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    prompts = {
        "uz": "Izohingizni yozib qoldiring:",
        "ru": "Напишите ваш комментарий:",
        "en": "Please write your comment:"
    }
    await message.answer(prompts.get(lang, prompts["ru"]))
    # Set state to wait for comment
    from states.registration import MenuState
    await state.set_state(MenuState.comment)

@router.message(lambda msg: msg.text in ["📜 Buyurtmalar tarixi", "📜 История заказов", "📜 Order History"])
async def history_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    telegram_id = str(message.from_user.id)
    
    # Get user info to get user_id
    user_info = await api_client.get_user(telegram_id)
    if not user_info:
        await message.answer(get_text("welcome", lang), reply_markup=get_language_keyboard())
        await state.set_state(RegisterState.language)
        return

    user_id = user_info.get("id")
    res = await api_client.get_user_orders(user_id)
    orders = res.get("items", [])
    
    if not orders:
        no_orders_text = {
            "uz": "Sizda hali buyurtmalar yo'q.",
            "ru": "У вас пока нет заказов.",
            "en": "You don't have any orders yet."
        }
        await message.answer(no_orders_text.get(lang, no_orders_text["ru"]))
        return
    
    # Format order list
    history_text = {
        "uz": "Sizning buyurtmalaringiz tarixi:\n\n",
        "ru": "Ваша история заказов:\n\n",
        "en": "Your order history:\n\n"
    }
    msg_text = history_text.get(lang, history_text["ru"])
    
    status_map = {
        "pending": "⏳",
        "confirmed": "✅",
        "declined": "❌"
    }
    
    for order in orders[:10]: # Show last 10 orders
        order_num = order.get("order_number", "???")
        status = order.get("status", "pending")
        date = order.get("created_at", "").split("T")[0]
        total = order.get("total_amount", 0)
        
        status_icon = status_map.get(status, "❓")
        msg_text += f"{status_icon} Order #{order_num} | {date} | {format_price(float(total))}\n"

    await message.answer(msg_text)


# Handler for Order button
@router.message(lambda msg: msg.text in ["📦 Buyurtma berish", "📦 Заказать", "📦 Order"])
async def order_handler(message: types.Message, state: FSMContext):
    """Start ordering - show root groups and search button"""
    data = await state.get_data()
    
    # Initialize state
    await state.update_data(
        cart=data.get("cart", []),
        groups_stack=[],
        current_items=[],
        item_name_map={},
        current_parent_id=None,
        current_page=0
    )
    
    from handlers.users.order import show_catalog
    has_items = await show_catalog(message, state, parent_id=None, page=0)
    
    if not has_items:
        await message.answer("No products available / Mahsulotlar mavjud emas / Нет доступных товаров")


# Handler for Language Change from Settings
from states.registration import MenuState
@router.message(MenuState.language)
async def change_language(message: types.Message, state: FSMContext):
    text = message.text
    if text not in LANG_MAP:
        await message.answer("Please select a button / Пожалуйста, выберите кнопку")
        return
    
    lang_code = LANG_MAP[text]
    await state.update_data(lang=lang_code)
    
    # Update language in backend
    telegram_id = str(message.from_user.id)
    await api_client.update_lang(telegram_id, lang_code)
    
    await message.answer(get_text("menu_main", lang_code), reply_markup=get_main_menu_keyboard(lang_code))
    await state.set_state(MenuState.main)

# Handler for Comment
@router.message(MenuState.comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Send comment to backend or admin
    # api_client.send_feedback(...)
    
    thanks = {
        "uz": "Rahmat! Izohingiz qabul qilindi.",
        "ru": "Спасибо! Ваш комментарий принят.",
        "en": "Thank you! Your comment has been received."
    }
    await message.answer(thanks.get(lang, thanks["ru"]), reply_markup=get_main_menu_keyboard(lang))
    await state.set_state(MenuState.main)
