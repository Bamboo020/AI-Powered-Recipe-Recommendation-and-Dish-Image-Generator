from app.ingredient_rules import contains_excluded, ingredient_matches_exclusion


def test_compound_ingredient_exclusions_use_token_boundaries():
    assert ingredient_matches_exclusion('peanut_butter', 'peanut')
    assert ingredient_matches_exclusion('egg_noodles', 'egg')
    assert not ingredient_matches_exclusion('peanut_butter', 'pea')
    assert not ingredient_matches_exclusion('nutmeg', 'nut')
    assert contains_excluded({'milk_chocolate', 'flour'}, {'milk'})
