from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from states.registration import OrderState, MenuState
from keyboards.default.catalog import (
    get_groups_keyboard,
    get_products_keyboard,
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


async def show_groups(message: types.Message, state: FSMContext, parent_id: str = None, extra_text: str = None):
    """Show groups at a particular level"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Fetch groups
    res = await api_client.get_groups(parent_id=parent_id)
    groups = res.get("items", [])
    
    if not groups:
        return False
    
    # Store groups and navigation stack
    groups_stack = data.get("groups_stack", [])
    if parent_id:
        groups_stack.append(parent_id)
    await state.update_data(
        current_groups=groups,
        current_parent_id=parent_id,
        groups_stack=groups_stack
    )
    
    is_root = parent_id is None
    category_text = get_text("select_category", lang)
    if extra_text:
        category_text = f"{extra_text}\n\n{category_text}"
    
    await message.answer(
        category_text,
        reply_markup=get_groups_keyboard(groups, lang, is_root=is_root)
    )
    
    # Show search button when at root level
    if is_root:
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


async def show_products(message: types.Message, state: FSMContext, group_id: str):
    """Show products for a group"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    res = await api_client.get_products(group_id=group_id)
    products = res.get("items", [])
    
    if not products:
        return False
    
    # Build product name mapping for easier lookup
    product_name_map = {}
    for prod in products:
        prod_name = prod.get(f"name_{lang}", prod.get("name_ru", prod.get("name", "Unknown")))
        normalized_name = prod_name.strip()
        product_name_map[normalized_name] = prod
    
    await state.update_data(
        current_products=products,
        product_name_map=product_name_map,
        current_group_id=group_id
    )
    
    await message.answer(
        get_text("select_product", lang),
        reply_markup=get_products_keyboard(products, lang)
    )
    await state.set_state(OrderState.product)
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
    
    # Fetch root groups (parent_id = null)
    has_groups = await show_groups(message, state, parent_id=None)
    
    if not has_groups:
        await message.answer("No groups found / Guruhlar topilmadi")


# --- Group Selected ---
@router.message(OrderState.group)
async def group_selected(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    current_parent_id = data.get("current_parent_id")
    groups_stack = data.get("groups_stack", [])
    
    # Check if back to menu (only for root level)
    if message.text == get_text("back_to_menu", lang):
        await message.answer(get_text("menu_main", lang), reply_markup=get_main_menu_keyboard(lang))
        await state.set_state(MenuState.main)
        return
    
    # Check if back (for non-root levels)
    if message.text == get_text("back", lang):
        if groups_stack:
            groups_stack.pop()  # Remove current level
            parent_id = groups_stack[-1] if groups_stack else None
            await state.update_data(groups_stack=groups_stack)
            await show_groups(message, state, parent_id=parent_id)
        else:
            # Go to root
            await state.update_data(groups_stack=[])
            await show_groups(message, state, parent_id=None)
        return
    
    # Check if view cart
    if message.text == get_text("view_cart", lang):
        await show_cart(message, state)
        return
    
    # Find group by name
    current_groups = data.get("current_groups", [])
    selected_group = None
    for group in current_groups:
        group_name = group.get(f"name_{lang}", group.get("name_ru", group.get("name", "")))
        if group_name == message.text:
            selected_group = group
            break
    
    if not selected_group:
        await message.answer("Group not found / Guruh topilmadi")
        return
    
    group_id = selected_group["id"]
    
    # Check if this group has child groups
    child_res = await api_client.get_groups(parent_id=group_id)
    child_groups = child_res.get("items", [])
    
    if child_groups:
        # Has children - navigate deeper
        await show_groups(message, state, parent_id=group_id)
    else:
        # No children - show products
        has_products = await show_products(message, state, group_id=group_id)
        if not has_products:
            await message.answer("No products found in this group / Bu guruhda mahsulotlar topilmadi")


# --- Product Selected ---
@router.message(OrderState.product)
async def product_selected(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Check if view cart
    if message.text == get_text("view_cart", lang):
        await show_cart(message, state)
        return
    
    # Check if back - go back to parent group
    if message.text == get_text("back", lang):
        current_group_id = data.get("current_group_id")
        groups_stack = data.get("groups_stack", [])
        
        # Pop current group from stack and show parent
        if groups_stack:
            parent_id = groups_stack[-1]
            await show_groups(message, state, parent_id=parent_id)
        else:
            await show_groups(message, state, parent_id=None)
        return
    
    # Find product using name mapping
    product_name_map = data.get("product_name_map", {})
    normalized_text = message.text.strip()
    
    selected_prod = product_name_map.get(normalized_text)
    
    # Fallback search
    if not selected_prod:
        products = data.get("current_products", [])
        for prod in products:
            prod_name = prod.get(f"name_{lang}", prod.get("name_ru", prod.get("name", "")))
            if prod_name.strip() == normalized_text:
                selected_prod = prod
                break
    
    if not selected_prod:
        logger.error(f"Product not found. Searched: '{normalized_text}', Available: {list(product_name_map.keys())}")
        await message.answer(f"Product not found / Mahsulot topilmadi")
        return
    
    prod_id = selected_prod["id"]
    
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
            
            # Download image and send as bytes
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


# --- Amount Entry ---
@router.message(OrderState.amount)
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
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
    await show_groups(message, state, parent_id=None, extra_text=confirmation)


# --- Cart Actions ---
@router.message(OrderState.cart)
async def cart_action(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    lang = data.get("lang", "ru")
    token = data.get("token")
    
    # Continue Shopping
    if message.text == get_text("continue_shopping", lang):
        # Go back to root groups
        await state.update_data(groups_stack=[])
        await show_groups(message, state, parent_id=None)
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
