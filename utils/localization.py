import json
import os
from data.config import ADMINS

# Load locales
LOCALES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "locales.json")
with open(LOCALES_PATH, "r", encoding="utf-8") as f:
    LOCALE_DATA = json.load(f)

def get_text(key: str, lang: str = "ru") -> str:
    """Get localized text."""
    try:
        return LOCALE_DATA[key][lang]
    except KeyError:
        return LOCALE_DATA[key]["ru"]  # Fallback


def format_price(amount) -> str:
    """Format price with $ currency.
    
    - Removes .00 (e.g., 100.00 -> $100)
    - Keeps meaningful decimals (e.g., 4.50 -> $4.5, 4.25 -> $4.25)
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0.0
    
    if amount == int(amount):
        return f"${int(amount):,}"
    else:
        # Remove trailing zeros from decimal
        formatted = f"{amount:,.2f}".rstrip('0').rstrip('.')
        return f"${formatted}"


# Language map for callback/text
LANG_MAP = {
    "🇺🇿 O'zbekcha": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}
