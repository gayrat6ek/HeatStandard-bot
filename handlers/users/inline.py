"""
Inline Mode Handler for Product Search

Simple Flow:
1. User types @bot_username <query> in any chat
2. Selects a product → Bot opens with product context (via switch_inline_query_current_chat)
3. Bot shows product info and asks "Enter quantity"
4. User types a number
5. Added to cart → Bot shows catalog to continue shopping
"""

from aiogram import Router, types, F
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from states.registration import OrderState
from keyboards.default.catalog import get_groups_keyboard
from utils.api import api_client
from utils.localization import get_text, format_price
from hashlib import md5
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.inline_query()
async def inline_product_search(inline_query: types.InlineQuery):
    """Handle inline queries for product search"""
    query = inline_query.query.strip()
    
    # If query is empty, show a hint
    if not query:
        results = [
            InlineQueryResultArticle(
                id="hint",
                title="🔍 Search for products",
                description="Type product name (e.g., radiator, valve)",
                input_message_content=InputTextMessageContent(
                    message_text="🔍 Enter product name to search..."
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    # Search products
    try:
        res = await api_client.search_products(query, limit=30)
        products = res.get("items", [])
        logger.info(f"Inline search for '{query}': got {len(products)} products")
    except Exception as e:
        logger.error(f"Inline search error: {e}")
        products = []
    
    if not products:
        results = [
            InlineQueryResultArticle(
                id="no_results",
                title="❌ No products found",
                description=f"No products matching '{query}'",
                input_message_content=InputTextMessageContent(
                    message_text=f"No products found for: {query}"
                )
            )
        ]
        await inline_query.answer(results, cache_time=10)
        return
    
    # Build inline results - each result opens bot with product ID
    results = []
    for product in products[:50]:
        try:
            prod_id = product.get("id", "")
            name_ru = product.get("name_ru", "Unknown")
            desc_ru = product.get("description_ru", "") or ""
            
            try:
                price = float(product.get("price", 0))
            except (ValueError, TypeError):
                price = 0.0
            
            images = product.get("images", [])
            result_id = md5(prod_id.encode()).hexdigest()
            
            # Short description for preview
            short_desc = desc_ru[:60] + "..." if len(desc_ru) > 60 else desc_ru
            
            # Message that will be sent - contains product ID for bot to detect
            message_text = f"🔧 {prod_id}"
            
            # Validate thumbnail URL (must be http/https)
            thumbnail = None
            if images and len(images) > 0:
                img_url = images[0]
                if img_url and (img_url.startswith("http://") or img_url.startswith("https://")):
                    thumbnail = img_url
            
            result = InlineQueryResultArticle(
                id=result_id,
                title=f"⚙️ {name_ru}",
                description=f"💰 {format_price(price)}" + (f" | {short_desc}" if short_desc else ""),
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="HTML"
                )
            )
            results.append(result)
        except Exception as e:
            logger.warning(f"Failed to build inline result for product {product.get('id')}: {e}")
    
    await inline_query.answer(
        results, 
        cache_time=1,
        switch_pm_text="🏗 Все товары",
        switch_pm_parameter="browse"
    )


# Handle product ID message from inline (when user selects product)
@router.message(F.text.startswith("🔧 "))
async def handle_inline_product_selection(message: types.Message, state: FSMContext):
    """Handle when user selects product from inline - show product and ask quantity"""
    # Extract product ID from message
    product_id = message.text.replace("🔧 ", "").strip()
    
    # Delete the product ID message (clean UX)
    try:
        await message.delete()
    except Exception:
        pass
    
    # Get user data
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Check if user is logged in
    token = data.get("token")
    if not token:
        telegram_id = str(message.from_user.id)
        login_res = await api_client.login_user(telegram_id)
        if "access_token" not in login_res:
            await message.answer("Please register first using /start")
            return
        token = login_res["access_token"]
        user = login_res.get("user", {})
        lang = user.get("current_lang", "ru")
        await state.update_data(token=token, lang=lang)
    
    # Fetch product details
    product = await api_client.get_product(product_id)
    if not product:
        await message.answer("Product not found / Mahsulot topilmadi")
        return
    
    name = product.get(f"name_{lang}", product.get("name_ru", "Unknown"))
    desc = product.get(f"description_{lang}", product.get("description_ru", "")) or ""
    
    try:
        price = float(product.get("price", 0))
    except (ValueError, TypeError):
        price = 0.0
    
    # Store product info
    await state.update_data(
        current_prod_id=product_id,
        current_prod=product,
        cart=data.get("cart", [])
    )
    
    images = product.get("images", [])
    
    # Show product info and ask for quantity with localized text
    text = (
        f"<b>{name}</b>\n"
        f"{desc[:100] if desc else ''}\n\n"
        f"{get_text('price', lang)}: {format_price(price)}\n\n"
        f"{get_text('enter_amount', lang)}"
    )
    
    # Send with image if available
    image_sent = False
    if images and len(images) > 0:
        img_url = images[0]
        try:
            # Convert localhost URLs to internal Docker network URL
            if "localhost" in img_url or "127.0.0.1" in img_url:
                # Replace localhost:8002 with backend service URL
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


# Deep-link handler for browse
@router.message(F.text == "/start browse")
async def start_browse(message: types.Message, state: FSMContext):
    """Handle browse deep-link - show main catalog"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Fetch root groups
    res = await api_client.get_groups(parent_id=None)
    groups = res.get("items", [])
    
    if groups:
        await state.update_data(
            current_groups=groups,
            current_parent_id=None,
            groups_stack=[]
        )
        await message.answer(
            get_text("select_category", lang),
            reply_markup=get_groups_keyboard(groups, lang, is_root=True)
        )
        await state.set_state(OrderState.group)
    else:
        await message.answer("No products available / Mahsulotlar mavjud emas")


@router.chosen_inline_result()
async def chosen_product(chosen_result: types.ChosenInlineResult):
    """Log when user selects an inline result"""
    logger.info(f"User {chosen_result.from_user.id} chose inline result: {chosen_result.result_id}")
