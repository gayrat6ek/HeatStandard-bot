from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.localization import get_text

def get_catalog_keyboard(items: list, lang: str, is_root: bool = True, page: int = 0, items_per_page: int = 50):
    """Create reply keyboard for unified catalog with pagination"""
    buttons = []
    
    # Add Cart and Back buttons at the TOP
    back_text = get_text("back_to_menu", lang) if is_root else get_text("back", lang)
    buttons.append([KeyboardButton(text=back_text), KeyboardButton(text=get_text("view_cart", lang))])
    
    # Calculate pagination
    total_items = len(items)
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = items[start_idx:end_idx]
    
    # Add items in rows of 2 for groups (type='group') and rows of 1 for products (type='product')
    # Since we combined them, we will just use rows of 2 for everything for consistency, or 1 for products.
    # Let's standardize on rows of 2 for a compact catalog, or 1 for products.
    # Actually, products have longer names. Let's do 1 per row for all items to not truncate text. Or 2 for groups and 1 for products.
    # We can determine type if it has 'price' or we can pass a list of dicts with a 'type' field.
    # Instead, let's just do 2 items per row if they are short, or 1 per row. To be safe, 1 per row.
    
    i = 0
    while i < len(page_items):
        item1 = page_items[i]
        name1 = item1.get(f"name_{lang}", item1.get("name_ru", item1.get("name", "Unknown")))
        
        # Check if it's a product (has price) or group. Products usually get 1 per row.
        is_product1 = "price" in item1
        
        if is_product1:
            buttons.append([KeyboardButton(text=name1)])
            i += 1
        else:
            row = [KeyboardButton(text=name1)]
            # Try to get second item if it's also a group
            if i + 1 < len(page_items):
                item2 = page_items[i + 1]
                is_product2 = "price" in item2
                if not is_product2:
                    name2 = item2.get(f"name_{lang}", item2.get("name_ru", item2.get("name", "Unknown")))
                    row.append(KeyboardButton(text=name2))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
            buttons.append(row)
            
    # Add Pagination Buttons if needed
    pagination_row = []
    if page > 0:
        pagination_row.append(KeyboardButton(text=get_text("prev", lang)))
    if end_idx < total_items:
        pagination_row.append(KeyboardButton(text=get_text("next", lang)))
        
    if pagination_row:
        buttons.append(pagination_row)
    
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
