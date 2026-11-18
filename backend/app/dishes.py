"""Heuristic category-to-recipe title mapping; no paired Food101/Food.com IDs."""
import re


def is_meal_candidate(recipe):
    """Meal-only discovery heuristic; not an assessment of nutrition or source completeness."""
    text = (recipe.get('title', '')+' '+recipe.get('source_category', '')).lower()
    if re.search(r'\b(cookies?|cakes?|desserts?|candy|candies|frosting|cocktails?|smoothies?|beverages?|chocolate|brownies?|icing|lemonade|milkshakes?)\b', text):
        return False
    category = recipe.get('source_category', '').lower()
    return not re.search(r'\b(sauces?|dressings?|condiments?|marinades?|seasonings?|beverages?)\b', category)


DISH_PATTERNS={
    'fried_rice':r'\bfried rice\b|炒饭',
    'omelette':r'\bomelette?s?\b|\bomelets?\b',
    'pizza':r'\bpizzas?\b',
    'ramen':r'\bramen\b',
    'dumplings':r'\bdumplings?\b|\bpot\s?stickers?\b|\bgyoza\b',
}

def matches_dish(recipe,category):
    title=recipe['title'].lower()
    if category=='pizza' and re.search(r'\b(dough|sauce|dip|seasoning|shells?|crusts?)\b',title):
        return False
    tags=' '.join(x for x in recipe.get('source_keywords',[]) if isinstance(x,str)).lower()
    if category=='dumplings' and re.search(r'\b(chips|salsa|dipping|sauce|wrappers?|skins?)\b',title):
        return False
    if category=='ramen' and 'broth' in title and not ('soup' in title or 'noodle' in title):
        return False
    if category=='dumplings' and not (re.search(r'\b(pot\s?stickers?|gyoza|wontons?|jiaozi)\b',title) or any(tag in tags for tag in ['chinese','asian','japanese','korean'])):
        return False
    if category=='ramen' and not ('soup' in title or 'broth' in title or 'soup' in recipe.get('source_category','').lower()):
        return False
    return bool(re.search(DISH_PATTERNS[category],title,re.I))
