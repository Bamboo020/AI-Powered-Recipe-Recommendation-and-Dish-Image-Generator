"""Real local API integration check. Two development photos are not an accuracy benchmark."""
import base64
import json
from pathlib import Path
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
SAMPLES=ROOT/'output/ingredient-smoke'
paths=[SAMPLES/'tomatoes.jpg',SAMPLES/'vegetables-eggs.jpg']
if not all(p.exists() for p in paths):
    raise SystemExit('Prepare the two attributed sample photos documented in data_metadata/ingredient_photo_sources.json, or use the UI with your own photos.')
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=300) as client:
    started=time.monotonic()
    response=client.post('/api/identify-ingredients',json={'images':[base64.b64encode(p.read_bytes()).decode() for p in paths]})
    response.raise_for_status();recognition=response.json()
    assert recognition['requires_confirmation'] and len(recognition['photos'])==2
    assert all(p['status']=='completed' for p in recognition['photos'])
    observed=[sorted({item['name'] for item in p['ingredients']}) for p in recognition['photos']]
    expected=[{'tomato'},{'egg','tomato','carrot','chili pepper'}]
    # Simulate an explicit human confirmation/correction, not automatic acceptance.
    confirmed=['tomato','egg','carrot','chili pepper']
    response=client.post('/api/recommend',json={'ingredients':confirmed,'max_cooking_time':30,'cuisine':'any','dataset':'real','servings':1,'top_k':3,'meal_only':True})
    response.raise_for_status();recipes=response.json()['recommendations']
    assert all(not any(word in r['title'].lower() for word in ['cookie','cake','brownie']) for r in recipes)
    assert recipes and all(r['recipe_id'].startswith('foodcom-') and r['total_minutes']<=30 for r in recipes)
    response=client.get('/api/food-resources/boston');response.raise_for_status();foods=response.json()
    assert any(e['full_meal'] is True for e in foods['events'])
    report={'verification':'Real HTTP ingredient photos → explicit correction → real recipe search, plus provider food-resource checks',
            'vision_model':recognition['model'],'recognition':recognition,
            'photo_review':[{'photo':paths[i].name,'expected_visible_ingredients':sorted(expected[i]),'observed_suggestions':names,'missed':sorted(expected[i]-set(names)),'extra':sorted(set(names)-expected[i])} for i,names in enumerate(observed)],
            'confirmed_ingredients':confirmed,
            'recipe_results':[{'recipe_id':r['recipe_id'],'title':r['title'],'total_minutes':r['total_minutes'],'source_url':r['source_url'],'matched':r['available_ingredients'],'missing':r['missing_ingredients']} for r in recipes],
            'food_resources':{'checked_at':foods['fetched_at'],'status':foods['status'],'program_count':len(foods['events']),'distinct_addresses':len({e['address'] for e in foods['events']}),'free_food_event_count':foods['free_food_event_count'],'source_checks':{e['title']:e['source_status'] for e in foods['events']}},
            'seconds':round(time.monotonic()-started,2),
            'limitations':['These two public photos are development smoke samples, not a held-out accuracy study.','LLaVA is pretrained; the visible-name mapping is a vocabulary heuristic, not a trained ingredient detector.','Manual confirmation uses known visible ingredients and includes corrections; it does not measure autonomous recognition accuracy.','Program source checks do not establish current food stock, exact menu, food safety or holiday service.']}
path=ROOT/'evaluation/results/food_and_photos_smoke.json';path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='recognition'},indent=2))
