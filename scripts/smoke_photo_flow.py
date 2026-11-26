"""Exercise real HTTP upload → predictions → explicit category confirmation → recipes."""
import json
from pathlib import Path
import time
import httpx
ROOT=Path(__file__).resolve().parents[1]
rows=[json.loads(line) for line in (ROOT/'data/processed/food101/test.jsonl').read_text().splitlines()]
cases=[]
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=120.) as client:
    health=client.get('/api/health').json()
    assert health['real_recipe_count']>=5000
    for category in ['dumplings','fried_rice','omelette','pizza','ramen']:
        row=next(r for r in rows if r['class_name']==category)
        started=time.monotonic()
        response=client.post('/api/classify-food',content=(ROOT/row['path']).read_bytes(),headers={'Content-Type':'image/jpeg'})
        response.raise_for_status();prediction=response.json()
        assert prediction['requires_confirmation'] is True
        # Test fixture acts as the user confirming/correcting the known class.
        result=client.post('/api/recommend',json={'ingredients':[],'dish_category':category,'dataset':'real','max_cooking_time':120,'top_k':3})
        result.raise_for_status();data=result.json()
        assert data['recommendations'] and all(r['recipe_id'].startswith('foodcom-') for r in data['recommendations'])
        cases.append({'image_id':row['image_id'],'path':row['path'],'known_class':category,'predictions':prediction['predictions'],'confirmed_category':category,'returned_recipe_ids':[r['recipe_id'] for r in data['recommendations']],'returned_titles':[r['title'] for r in data['recommendations']],'seconds':round(time.monotonic()-started,2)})
        print(json.dumps(cases[-1]),flush=True)
report={'health':health,'test_policy':'First official test image by sorted ID for each supported class; class confirmation uses known class, correcting the model if needed. This is a five-case integration check, not the accuracy benchmark.','cases':cases,'completed':len(cases)}
(ROOT/'evaluation/results/photo_flow_smoke.json').write_text(json.dumps(report,indent=2)+'\n')
