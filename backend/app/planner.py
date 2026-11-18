"""Transparent lifestyle preferences, not clinical nutrition prescriptions."""
from datetime import datetime, timedelta
from enum import Enum
import re
from pydantic import BaseModel, Field, model_validator


class Goal(str, Enum):
    balanced = 'balanced'
    maintain = 'maintain'
    weight_management = 'weight_management'
    strength = 'strength'
    endurance = 'endurance'
    plant_variety = 'plant_variety'
    save_time = 'save_time'
    budget = 'budget'
    reduce_waste = 'reduce_waste'


GOALS = {
    'balanced': ('Balanced eating', 'Look for a mix of vegetables, protein foods and grains across meals.'),
    'maintain': ('Maintain weight', 'Keep regular meals and adjust portions to your usual needs; no automatic calorie deficit.'),
    'weight_management': ('Weight management', 'Compare portions and available nutrition without skipping meals or prescribing a calorie deficit.'),
    'strength': ('Strength & muscle', 'Prefer recipes listing a protein food; this does not establish a protein target.'),
    'endurance': ('Endurance & active days', 'Prefer recipes combining a carbohydrate food and a protein food.'),
    'plant_variety': ('More plants & fiber', 'Prefer vegetable, fruit, bean and whole-grain ingredients; fiber grams may be unknown.'),
    'save_time': ('Save time', 'Prefer shorter source-reported total preparation and cooking times.'),
    'budget': ('Spend less', 'Prefer fewer missing ingredients as a shopping proxy; prices are not available.'),
    'reduce_waste': ('Use up the pantry', 'Prefer recipes using more of the ingredients you already have.'),
}
PROTEIN = ('egg', 'chicken', 'tofu', 'bean', 'lentil', 'fish', 'salmon', 'beef', 'yogurt', 'turkey')
CARB = ('rice', 'pasta', 'noodle', 'potato', 'oat', 'bread', 'quinoa', 'barley')
PLANTS = ('tomato', 'broccoli', 'spinach', 'carrot', 'cabbage', 'pea', 'bean', 'lentil', 'apple', 'berry', 'oat', 'whole wheat', 'onion', 'pepper')


def contains_food(text, word):
    return bool(re.search(r'\b'+re.escape(word)+r'(?:s|es)?\b', text))


class PlanRequest(BaseModel):
    goals: list[Goal] = Field(default_factory=lambda: [Goal.balanced], min_length=1, max_length=9)
    ingredients: list[str] = Field(default_factory=list, max_length=50)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=50)
    window_start: datetime
    meal_at: datetime
    hemisphere: str = Field(default='north', pattern='^(north|south|tropical)$')
    willing_to_cook: bool = True

    @model_validator(mode='after')
    def valid_window(self):
        if self.window_start.utcoffset() is None or self.meal_at.utcoffset() is None:
            raise ValueError('Times must include a UTC offset')
        minutes = (self.meal_at - self.window_start).total_seconds() / 60
        if minutes < 1 or minutes > 1440:
            raise ValueError('Choose a free cooking window between 1 minute and 24 hours')
        if Goal.maintain in self.goals and Goal.weight_management in self.goals:
            raise ValueError('Choose either maintain weight or weight management')
        return self


def season_for(month, hemisphere):
    if hemisphere == 'tropical':
        return 'Local wet/dry season varies; check local produce availability'
    index = (month % 12) // 3
    return ['Winter', 'Spring', 'Summer', 'Autumn'][(index + (2 if hemisphere == 'south' else 0)) % 4]


def plan(request, recipes, normalize):
    available = {normalize(x) for x in request.ingredients if x.strip()}
    excluded = {normalize(x) for x in request.excluded_ingredients if x.strip()}
    window = (request.meal_at-request.window_start).total_seconds()/60
    ranked = []
    for recipe in recipes:
        if not recipe['recipe_id'].startswith('foodcom-'):
            continue
        # This endpoint plans meals, not desserts or drinks that happen to contain eggs/oats.
        category_text = (recipe.get('source_category', '')+' '+recipe.get('title', '')).lower()
        if re.search(r'\b(cookie|cookies|cake|cakes|dessert|desserts|candy|candies|frosting|cocktail|cocktails|smoothie|beverage|beverages|chocolate|brownie|brownies)\b', category_text):
            continue
        duration = recipe.get('total_minutes')
        needed = {normalize(i['name']) for i in recipe['ingredient_items']}
        if not duration or duration > window or not needed or needed & excluded:
            continue
        matched = needed & available
        if available and not matched:
            continue
        text = ' '.join(needed).replace('_', ' ')
        protein = any(contains_food(text, word) for word in PROTEIN)
        carb = any(contains_food(text, word) for word in CARB)
        plants = sum(contains_food(text, word) for word in PLANTS)
        factors = {'balanced': (protein + bool(plants) + carb)/3,
                   'maintain': (protein + bool(plants) + carb)/3,
                   'weight_management': (protein + bool(plants))/2,
                   'strength': float(protein), 'endurance': (protein+carb)/2,
                   'plant_variety': min(plants/3, 1), 'save_time': 1-duration/window,
                   'budget': 1/(1+len(needed-available)),
                   'reduce_waste': len(matched)/max(1,len(available))}
        selected = {g.value: round(factors[g.value], 3) for g in dict.fromkeys(request.goals)}
        score = .6*sum(selected.values())/len(selected) + .4*len(matched)/len(needed)
        ranked.append({**recipe, 'goal_factors': selected, 'planning_score': round(score, 3),
                       'matched_ingredients': sorted(matched), 'missing_ingredients': sorted(needed-available),
                       'cook_start': (request.meal_at-timedelta(minutes=duration)).isoformat(),
                       'meal_at': request.meal_at.isoformat()})
    ranked.sort(key=lambda r: (-r['planning_score'], r['total_minutes'], r['recipe_id']))
    season = season_for(request.meal_at.month, request.hemisphere)
    seasonal_note = {'Winter': 'Try a warm soup or cooked vegetables using locally available produce.',
                     'Spring': 'Consider locally available leafy greens.',
                     'Summer': 'Consider a cool meal and locally available vegetables.',
                     'Autumn': 'Consider locally available squash or root vegetables.'}.get(season, 'Use local seasonal information for produce choices.')
    decision = ('Cooking fits your free window. Compare missing ingredients and source quantities before deciding.' if ranked and request.willing_to_cook else
                'A ready-to-eat meal can fit a busy day. Compare protein foods, vegetables and portions. Explore Boston activities below to make time for something you enjoy.')
    return {'goals': [{'id': g.value, 'label': GOALS[g.value][0], 'guidance': GOALS[g.value][1]} for g in dict.fromkeys(request.goals)],
            'season': season, 'seasonal_note': seasonal_note,
            'season_basis': 'Calendar season by selected hemisphere; a planning prompt, not a local harvest or weather forecast. Season does not change recipe scores.',
            'free_minutes': round(window), 'recipes': ranked[:3], 'decision': decision,
            'activity': {'suggestion': 'If comfortable, choose a short walk or movement break. For strength goals, plan resistance training on separate days; start at a level that suits your ability.',
                         'weekly_context': 'General adult guidance: at least 150 minutes of moderate activity per week and muscle strengthening on 2 days. This meal plan does not calculate exercise calorie burn.',
                         'source_url': 'https://www.cdc.gov/physical-activity-basics/guidelines/adults.html'},
            'limitations': ['Goal scores are ingredient keyword heuristics, not validated health outcomes. Ranking blends 60% selected goal fit and 40% pantry coverage; obvious desserts and drinks are excluded by title/category rules.',
                           'Cooking time uses source total time; shopping, thawing and cleanup are not included. Your selected window must be free of other commitments.',
                           'Recipe quantities retain the original yield. Reported nutrition has not been independently verified; no daily calorie or macro prescription is generated.',
                           'Exclusions match ingredient names only and cannot guarantee allergy safety. Medical conditions, pregnancy and children require tailored professional guidance.']}
