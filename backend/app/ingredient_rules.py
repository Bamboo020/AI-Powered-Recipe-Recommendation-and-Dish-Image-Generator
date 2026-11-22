"""Conservative boundary-aware matching for normalized ingredient exclusions."""
import re


def ingredient_matches_exclusion(ingredient, exclusion):
    ingredient = ingredient.strip().lower().replace(" ", "_")
    exclusion = exclusion.strip().lower().replace(" ", "_")
    if not ingredient or not exclusion:
        return False
    if ingredient == exclusion:
        return True
    pattern = rf"(?:^|_){re.escape(exclusion)}(?:s|es)?(?:_|$)"
    return bool(re.search(pattern, ingredient))


def contains_excluded(ingredients, exclusions):
    return any(ingredient_matches_exclusion(ingredient, exclusion)
               for ingredient in ingredients for exclusion in exclusions)
