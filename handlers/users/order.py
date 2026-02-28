from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from states.registration import OrderState, MenuState
from keyboards.default.catalog import (
    get_catalog_keyboard,
    get_cart_keyboard
)
from keyboards.default.menu import get_main_menu_keyboard
from utils.api import api_client
from utils.localization import get_text, format_price
import logging

router = Router()
router.message.filter(F.chat.type == "private")
logger = logging.getLogger(__name__)

# --- Helper Functions ---
async def show_cart(message: types.Message, state: FSMContext):
    """Show cart summary"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    cart = data.get("cart", [])
    
    if not cart:
        await message.answer(get_text("cart_empty", lang))
        return
    
    # Show Cart Summary
    total = sum(float(item['price']) * float(item['quantity']) for item in cart)
    cart_items_text = "\n".join([
        f"• {item['product_name']} x {item['quantity']} = {format_price(float(item['price']) * float(item['quantity']))}"
        for item in cart
    ])
    cart_summary = f"🛒 Your Cart:\n\n{cart_items_text}\n\n💰 Total: {format_price(total)}"
    
    await message.answer(
        cart_summary,
        reply_markup=get_cart_keyboard(lang)
    )
    await state.set_state(OrderState.cart)


async def show_catalog(message: types.Message, state: FSMContext, parent_id: str = None, page: int = 0, extra_text: str = None):
    """Show unified catalog (groups and products) with pagination"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Fetch groups and products
    groups_res = await api_client.get_groups(parent_id=parent_id)
    groups = groups_res.get("items", [])
    
    products = []
    if parent_id:
        products_res = await api_client.get_products(group_id=parent_id)
        products = products_res.get("items", [])
        
    items = groups + products
    
    if not items and parent_id is not None:
        return False
        
    # Store mapping for easy lookup
    item_name_map = {}
    for item in items:
        name = item.get(f"name_{lang}", item.get("name_ru", item.get("name", "Unknown")))
        item_name_map[name.strip()] = item
        
    # Store groups and navigation stack
    groups_stack = data.get("groups_stack", [])
    if parent_id:
        if not groups_stack or groups_stack[-1] != parent_id:
            groups_stack.append(parent_id)
    else:
        groups_stack = []
        
    await state.update_data(
        current_items=items,
        item_name_map=item_name_map,
        current_parent_id=parent_id,
        groups_stack=groups_stack,
        current_page=page
    )
    
    is_root = parent_id is None
    category_text = get_text("select_category", lang) if is_root else get_text("select_product", lang)
    if extra_text:
        category_text = f"{extra_text}\n\n{category_text}"
    
    await message.answer(
        category_text,
        reply_markup=get_catalog_keyboard(items, lang, is_root=is_root, page=page)
    )
    
    # Show search button when at root level
    if is_root and page == 0:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        search_btn_texts = {
            "uz": "🔍 Mahsulot qidirish",
            "ru": "🔍 Поиск товаров", 
            "en": "🔍 Search products"
        }
        search_hint_texts = {
            "uz": "Yoki ushbu tugma bilan qidiring 👇",
            "ru": "Или найдите товар с помощью кнопки 👇",
            "en": "Or search using the button below 👇"
        }
        search_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=search_btn_texts.get(lang, search_btn_texts["ru"]),
                switch_inline_query_current_chat=""
            )]
        ])
        await message.answer(
            search_hint_texts.get(lang, search_hint_texts["ru"]),
            reply_markup=search_keyboard
        )
    
    await state.set_state(OrderState.group)
    return True


# --- Entry Point ---
@router.message(F.text.in_(["🛍 Buyurtma berish", "🛍 Заказать", "🛍 Order"]))
async def start_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Initialize state
    await state.update_data(
        cart=data.get("cart", []),
        groups_stack=[],
        current_groups=[],
        current_products=[],
        current_parent_id=None
    )
    
    # Fetch root catalog (parent_id = null)
    has_items = await show_catalog(message, state, parent_id=None, page=0)
    
    if not has_items:
        await message.answer("No items found / Ma'lumot topilmadi")


# --- Catalog Selected ---
@router.message(OrderState.group, ~F.text.startswith("/"))
@router.message(OrderState.product, ~F.text.startswith("/")) # Fallback mapping
async def catalog_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    current_parent_id = data.get("current_parent_id")
    groups_stack = data.get("groups_stack", [])
    current_page = data.get("current_page", 0)
    
    # Check pagination
    if message.text == get_text("prev", lang):
        await show_catalog(message, state, parent_id=current_parent_id, page=max(0, current_page - 1))
        return
    if message.text == get_text("next", lang):
        await show_catalog(message, state, parent_id=current_parent_id, page=current_page + 1)
        return
        
    # Check if back to menu (only for root level)
    if message.text == get_text("back_to_menu", lang):
        await message.answer(get_text("menu_main", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.set_state(MenuState.main)
        return
    
    # Check if back
    if message.text == get_text("back", lang):
        if groups_stack:
            groups_stack.pop()  # Remove current level
            parent_id = groups_stack[-1] if groups_stack else None
            await state.update_data(groups_stack=groups_stack)
            await show_catalog(message, state, parent_id=parent_id, page=0)
        else:
            await state.update_data(groups_stack=[])
            await show_catalog(message, state, parent_id=None, page=0)
        return
    
    # Check if view cart
    if message.text == get_text("view_cart", lang):
        await show_cart(message, state)
        return
    
    item_name_map = data.get("item_name_map", {})
    normalized_text = message.text.strip()
    selected_item = item_name_map.get(normalized_text)
    
    # Fallback search
    if not selected_item:
        items = data.get("current_items", [])
        for item in items:
            item_name = item.get(f"name_{lang}", item.get("name_ru", item.get("name", "")))
            if item_name.strip() == normalized_text:
                selected_item = item
                break
                
    if not selected_item:
        logger.error(f"Item not found. Searched: '{normalized_text}', Available: {list(item_name_map.keys())}")
        await message.answer("Item not found / Element topilmadi")
        return
        
    # Determine if it's a group or product
    if "price" in selected_item: # It's a product
        prod_id = selected_item["id"]
        
        # Fetch full product details
        product = await api_client.get_product(prod_id)
        if not product:
            await message.answer("Product details not available")
            return
    
        # Store product info for cart
        await state.update_data(current_prod_id=prod_id, current_prod=product)
    
        name = product.get(f"name_{lang}", product.get("name_ru", product.get("name", "Unknown")))
        desc = product.get(f"description_{lang}", product.get("description_ru", product.get("description", "")))
        price = product.get("price", 0)
        images = product.get("images", [])
        
        text = f"<b>{name}</b>\n\n{desc}\n\n{get_text('price', lang)}: {format_price(price)}\n\n{get_text('enter_amount', lang)}"
        
        # Send image with caption if product has images
        image_sent = False
        if images and len(images) > 0:
            img_url = images[0]
            try:
                # Convert localhost URLs to internal Docker network URL
                if "localhost" in img_url or "127.0.0.1" in img_url:
                    img_url = img_url.replace("http://localhost:8002", "http://app:8000")
                    img_url = img_url.replace("http://127.0.0.1:8002", "http://app:8000")
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            from aiogram.types import BufferedInputFile
                            photo = BufferedInputFile(image_data, filename="product.jpg")
                            await message.answer_photo(
                                photo=photo,
                                caption=text,
                                parse_mode="HTML"
                            )
                            image_sent = True
                        else:
                            logger.warning(f"Failed to download image: HTTP {response.status}")
            except Exception as e:
                logger.warning(f"Failed to send product image: {e}")
        
        if not image_sent:
            await message.answer(text, parse_mode="HTML")
        
        await state.set_state(OrderState.amount)
    else:
        # It's a group
        group_id = selected_item["id"]
        # Navigate deeper
        has_items = await show_catalog(message, state, parent_id=group_id, page=0)
        if not has_items:
             await message.answer("No products found in this category / Bu kategoriyada mahsulotlar topilmadi")

# --- Amount Entry ---
@router.message(OrderState.amount, ~F.text.startswith("/"))
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Handle Back button
    if message.text == get_text("back", lang):
        current_parent_id = data.get("current_parent_id")
        current_page = data.get("current_page", 0)
        await show_catalog(message, state, parent_id=current_parent_id, page=current_page)
        return
        
    # Handle View Cart button
    if message.text == get_text("view_cart", lang):
        await show_cart(message, state)
        return
    
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a valid number")
        return

    # Add to cart
    cart = data.get("cart", [])
    product = data.get("current_prod")
    product_name = product.get(f"name_{lang}", product.get("name_ru", product.get("name", "Unknown")))
    
    cart.append({
        "product_id": product["id"],
        "iiko_product_id": product.get("iiko_id", ""),
        "quantity": amount,
        "price": float(product["price"]) if product.get("price") else 0,
        "product_name": product_name
    })
    
    await state.update_data(cart=cart, groups_stack=[])
    
    # Confirmation + category selection in one message
    confirmations = {
        "uz": f"{product_name} ✅ savatga qo'shildi",
        "ru": f"{product_name} ✅ добавлен в корзину",
        "en": f"{product_name} ✅ added to cart"
    }
    confirmation = confirmations.get(lang, confirmations["ru"])
    
    # Redirect back to root groups to continue shopping
    await state.update_data(groups_stack=[])
    await show_catalog(message, state, parent_id=None, page=0, extra_text=confirmation)


# --- Cart Actions ---
@router.message(OrderState.cart, ~F.text.startswith("/"))
async def cart_action(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    lang = data.get("lang", "ru")
    token = data.get("token")
    
    # Continue Shopping
    if message.text == get_text("continue_shopping", lang):
        # Go back to root groups
        await state.update_data(groups_stack=[])
        await show_catalog(message, state, parent_id=None, page=0)
        return
    
    # Clear Cart
    if message.text == get_text("clear_cart", lang):
        await state.update_data(cart=[])
        await message.answer(get_text("cart_empty", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.set_state(MenuState.main)
        return
    
    # Back to Menu
    if message.text == get_text("back_to_menu", lang):
        await message.answer(get_text("menu_main", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.set_state(MenuState.main)
        return
    
    # Checkout
    if message.text == get_text("checkout", lang):
        if not cart:
            await message.answer(get_text("cart_empty", lang))
            return
            
        if not token:
            await message.answer("Session expired, please /start")
            return

        # Get organization_id from first product
        first_org_id = None
        if cart:
            p_id = cart[0]["product_id"]
            p_details = await api_client.get_product(p_id)
            if p_details:
                first_org_id = p_details.get("organization_id")
        
        # Get user info
        telegram_id = str(message.from_user.id)
        user_info = await api_client.get_user(telegram_id)
        
        # Get customer info with fallbacks
        customer_name = "Telegram User"
        customer_phone = "+998900000000"  # Fallback phone
        
        if user_info:
            user_id = user_info.get("id")
            customer_name = user_info.get("full_name") or message.from_user.full_name or "Telegram User"
            phone = user_info.get("phone_number", "")
            if phone and phone.strip():
                customer_phone = phone.strip()
        else:
            await message.answer("User profile not found. Please /start again.")
            return
        
        logger.info(f"Creating order: customer={customer_name}, phone={customer_phone}, user_id={user_id}")
        
        payload = {
            "organization_id": first_org_id,
            "items": [
                {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": int(item["quantity"]),
                    "price": float(item["price"]),
                    "total": float(item["price"]) * float(item["quantity"])
                }
                for item in cart
            ],
            "customer_name": customer_name,
            "customer_phone": customer_phone,
        }
        
        res = await api_client.create_order(payload, user_id)
        
        if "error" in res:
            await message.answer(f"Error: {res['error']}")
        else:
            order_number = res.get("order_number", "N/A")
            order_id = res.get("id")
            total_amount = res.get("total_amount", sum(float(item["price"]) * float(item["quantity"]) for item in cart))
            
            # Tell user their order is pending
            msg = get_text("order_created", lang).format(id=order_number)
            await message.answer(msg)
            await state.update_data(cart=[])
            
            # Send order to admin group
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Build order details message
            items_text = "\n".join([
                f"  • {item['product_name']} × {int(item['quantity'])} = {format_price(float(item['price']) * float(item['quantity']))}"
                for item in cart
            ])
            
            admin_message = (
                f"🆕 <b>Новый заказ #{order_number}</b>\n\n"
                f"👤 <b>Клиент:</b> {customer_name}\n"
                f"📞 <b>Телефон:</b> {customer_phone}\n\n"
                f"<b>Товары:</b>\n{items_text}\n\n"
                f"💰 <b>Итого:</b> {format_price(float(total_amount))}\n\n"
                f"🕐 Ожидает подтверждения"
            )
            
            # Admin action buttons
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order_accept:{order_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_decline:{order_id}")
                ]
            ])
            
            # Send to admin group
            from data.config import ADMIN_GROUP_ID
            from loader import bot
            try:
                admin_msg = await bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=admin_message,
                    parse_mode="HTML",
                    reply_markup=admin_keyboard
                )
                # Save message ID for later editing
                await api_client.update_order_message_id(order_id, admin_msg.message_id)
            except Exception as e:
                logger.error(f"Failed to send order to admin group: {e}")
            
            await message.answer(get_text("menu_main", lang), reply_markup=get_main_menu_keyboard(lang))
            await state.set_state(MenuState.main)
        return
    
    await message.answer("Please select an option from the keyboard")
