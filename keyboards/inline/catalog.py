from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.localization import get_text

def get_categories_markup(categories: list, lang: str):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        # Use name_{lang} if available, else name
        # Assuming backend returns name_uz, name_ru, name_en
        # or simplified name based on request but client logic handles it usually.
        # The API client returns raw JSON
        name = cat.get(f"name_{lang}", cat.get("name", "Unknown"))
        builder.button(text=name, callback_data=f"cat_{cat['id']}")
    
    builder.adjust(2)
    return builder.as_markup()

def get_subcategories_markup(subcategories: list, lang: str):
    builder = InlineKeyboardBuilder()
    for sub in subcategories:
        name = sub.get(f"name_{lang}", sub.get("name", "Unknown"))
        builder.button(text=name, callback_data=f"sub_{sub['id']}")
    
    builder.button(text=get_text("back", lang), callback_data="back_cats")
    builder.adjust(2)
    return builder.as_markup()

def get_products_markup(products: list, lang: str):
    builder = InlineKeyboardBuilder()
    for prod in products:
        name = prod.get(f"name_{lang}", prod.get("name", "Unknown"))
        builder.button(text=name, callback_data=f"prod_{prod['id']}")
        
    builder.button(text=get_text("back", lang), callback_data="back_subs")
    builder.adjust(1)
    return builder.as_markup()

def get_product_detail_markup(product_id: str, lang: str):
    builder = InlineKeyboardBuilder()
    # Quantity controls and Add to Cart could be here, or simplified to "Enter Amount" via message
    # Let's do a simple "Add to Cart" button which triggers amount input
    builder.button(text=get_text("add_to_cart", lang), callback_data=f"add_{product_id}")
    builder.button(text=get_text("back", lang), callback_data="back_prods")
    builder.adjust(1)
    return builder.as_markup()

def get_cart_markup(cart_items: list, lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("checkout", lang), callback_data="checkout")
    builder.button(text=get_text("clear_cart", lang), callback_data="clear_cart")
    builder.button(text=get_text("back", lang), callback_data="back_menu")
    builder.adjust(1)
    return builder.as_markup()
