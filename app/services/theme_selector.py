import random

# Predefined list of shop themes
SHOP_THEMES = [
    "clothing",
    "electronics",
    "home decor",
    "beauty",
    "sports",
    "books",
    "toys",
    "jewelry",
    "automotive",
    "health"
]

def select_random_theme() -> str:
    """
    Randomly selects a theme for the online shop from the predefined list.

    Returns:
        str: Randomly selected shop theme
    """
    return random.choice(SHOP_THEMES)
