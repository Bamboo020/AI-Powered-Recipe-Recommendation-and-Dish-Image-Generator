from datetime import datetime
import pytest
from pydantic import ValidationError
from app.planner import PlanRequest, plan, season_for


def request(**kwargs):
    return PlanRequest(window_start='2026-11-17T17:30:00-05:00', meal_at='2026-11-17T18:30:00-05:00', **kwargs)


def recipe(key, ingredients, minutes=20):
    return {'recipe_id':'foodcom-'+key,'title':key,'total_minutes':minutes,'ingredient_items':[{'name':x} for x in ingredients], 'servings':2}


def test_goals_change_ranking_and_missing_values_stay_unknown():
    recipes=[recipe('a',['potato']),recipe('b',['egg','spinach'])]
    result=plan(request(goals=['strength']), recipes, str.lower)
    assert result['recipes'][0]['title']=='b'
    assert 'nutrition' not in result['recipes'][0]
    assert 'takeout' not in result


def test_window_and_exclusions_are_hard_constraints():
    result=plan(request(excluded_ingredients=['egg']),[recipe('a',['egg']),recipe('b',['potato'],61),recipe('c',['potato'],20)],str.lower)
    assert [r['title'] for r in result['recipes']]==['c']
    assert result['recipes'][0]['cook_start']=='2026-11-17T18:10:00-05:00'


def test_overnight_and_southern_season():
    req=PlanRequest(window_start='2026-12-31T23:40:00+11:00',meal_at='2027-01-01T00:10:00+11:00',hemisphere='south')
    result=plan(req,[recipe('a',['egg'])],str.lower)
    assert result['season']=='Summer'
    assert result['recipes'][0]['cook_start'].startswith('2026-12-31T23:50')
    assert season_for(7,'north')=='Summer'


def test_invalid_or_conflicting_preferences():
    with pytest.raises(ValidationError):
        request(goals=['maintain','weight_management'])
    with pytest.raises(ValidationError):
        PlanRequest(window_start='2026-11-17T18:00:00',meal_at='2026-11-17T19:00:00')
    with pytest.raises(ValidationError):
        request(goals=['crash_diet'])


def test_ready_meal_option_does_not_invent_businesses():
    result=plan(request(willing_to_cook=False),[recipe('cook-me',['egg'])],str.lower)
    assert 'takeout' not in result
    assert 'ready-to-eat' in result['decision']
    assert result['planning_mode']=='ready_to_eat'
    assert result['recipes']==[]
    assert result['ready_to_eat_resources_endpoint']=='/api/food-resources/boston'


def test_desserts_and_substring_matches_do_not_become_balanced_meals():
    from app.planner import contains_food
    assert not contains_food('peanut butter','pea')
    cake=recipe('Chocolate Cake',['egg','oat','potato'])
    result=plan(request(),[cake,recipe('b',['egg','potato','spinach'])],str.lower)
    assert [r['title'] for r in result['recipes']]==['b']
