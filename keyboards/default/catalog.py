from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.localization import get_text

def get_groups_keyboard(groups: list, lang: str, is_root: bool = True):
    """Create reply keyboard for groups (both root and child levels)"""
    buttons = []
    
    # Add Cart and Back buttons at the TOP
    back_text = get_text("back_to_menu", lang) if is_root else get_text("back", lang)
    buttons.append([KeyboardButton(text=back_text), KeyboardButton(text=get_text("view_cart", lang))])
    
    # Add groups in rows of 2
    for i in range(0, len(groups), 2):
        row = []
        for j in range(i, min(i + 2, len(groups))):
            group = groups[j]
            name = group.get(f"name_{lang}", group.get("name_ru", group.get("name", "Unknown")))
            row.append(KeyboardButton(text=name))
        buttons.append(row)
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def get_products_keyboard(products: list, lang: str):
    """Create reply keyboard for products"""
    buttons = []
    
    # Add Cart and Back buttons at the TOP
    buttons.append([KeyboardButton(text=get_text("back", lang)), KeyboardButton(text=get_text("view_cart", lang))])
    
    # Add products in single column for better readability
    for prod in products:
        name = prod.get(f"name_{lang}", prod.get("name_ru", prod.get("name", "Unknown")))
        buttons.append([KeyboardButton(text=name)])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def get_cart_keyboard(lang: str):
    """Create reply keyboard for cart actions"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("checkout", lang)), KeyboardButton(text=get_text("clear_cart", lang))],
            [KeyboardButton(text=get_text("continue_shopping", lang)), KeyboardButton(text=get_text("back_to_menu", lang))]
        ],
        resize_keyboard=True
    )

# Backwards compatibility aliases
def get_categories_keyboard(categories: list, lang: str):
    """Alias for get_groups_keyboard for root groups"""
    return get_groups_keyboard(categories, lang, is_root=True)

def get_subcategories_keyboard(subcategories: list, lang: str):
    """Alias for get_groups_keyboard for child groups"""
    return get_groups_keyboard(subcategories, lang, is_root=False)

def get_product_detail_keyboard(lang: str):
    """Create reply keyboard for product details (deprecated)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("add_to_cart", lang))],
            [KeyboardButton(text=get_text("back", lang))]
        ],
        resize_keyboard=True
    )
