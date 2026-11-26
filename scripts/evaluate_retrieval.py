"""Reproducible silver query reconstruction benchmark, not human relevance labels."""
import json
from pathlib import Path
import random
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app import main


def evaluate():
    rng=random.Random(2026)
    original_reader=main.read_recipes
    main.read_recipes=lambda:recipes_all
    recipes=[r for r in main.read_recipes() if r['recipe_id'].startswith('foodcom-') and 3<=len(r['ingredient_items'])<=8 and r['total_minutes']<=45]
    targets=rng.sample(sorted(recipes,key=lambda r:r['recipe_id']),20)
    queries=[]
    for target in targets:
        ingredients=sorted({main.normalize(i['name']) for i in target['ingredient_items']})
        chosen=rng.sample(ingredients,min(3,len(ingredients)))
        queries.append({'ingredients':chosen,'max_cooking_time':target['total_minutes'],'cuisine':'any','dataset':'real','top_k':10,'known_positive_recipe_id':target['recipe_id']})
    results={key:[] for key in ['keyword_jaccard','ingredient_rules_v1','hybrid_semantic_v1']}
    real_encoder=main.semantic_scores
    with TestClient(main.app) as client:
        for n,query in enumerate(queries):
            payload={k:v for k,v in query.items() if k!='known_positive_recipe_id'}
            positive=query['known_positive_recipe_id'];available=set(query['ingredients'])
            eligible=[r for r in recipes_all if r['total_minutes']<=query['max_cooking_time'] and available & {main.normalize(i['name']) for i in r['ingredient_items']}]
            keyword=sorted(eligible,key=lambda r:(-len(available & {main.normalize(i['name']) for i in r['ingredient_items']})/len(available | {main.normalize(i['name']) for i in r['ingredient_items']}),r['recipe_id']))[:10]
            ids=[r['recipe_id'] for r in keyword]
            results['keyword_jaccard'].append({'rank':ids.index(positive)+1 if positive in ids else None})
            for name,encoder in [('ingredient_rules_v1',lambda q,r:None),('hybrid_semantic_v1',real_encoder)]:
                main.semantic_scores=encoder;started=time.monotonic()
                response=client.post('/api/recommend',json=payload);response.raise_for_status();data=response.json()
                ids=[r['recipe_id'] for r in data['recommendations']]
                violations=sum(r['total_minutes']>query['max_cooking_time'] for r in data['recommendations'])
                results[name].append({'rank':ids.index(positive)+1 if positive in ids else None,'seconds':time.monotonic()-started,'time_violations':violations,'actual_method':data['ranking_method']})
            print(f'evaluated {n+1}/{len(queries)}',flush=True)
    main.semantic_scores=real_encoder
    main.read_recipes=original_reader
    summary={}
    for method,rows in results.items():
        summary[method]={'queries':len(rows),'known_positive_hit_at_3':sum(r['rank'] is not None and r['rank']<=3 for r in rows)/len(rows),'known_positive_hit_at_10':sum(r['rank'] is not None for r in rows)/len(rows),'known_positive_mrr_at_10':sum(1/r['rank'] if r['rank'] else 0 for r in rows)/len(rows)}
        if 'seconds' in rows[0]:summary[method].update(mean_seconds=sum(r['seconds'] for r in rows)/len(rows),time_violations=sum(r['time_violations'] for r in rows),semantic_fallbacks=sum(r['actual_method']!='hybrid_semantic_v1' for r in rows) if method=='hybrid_semantic_v1' else None)
    report={'seed':2026,'dataset_count':len(recipes_all),'query_construction':'20 seeded source recipes; three ingredient names as query, source duration as budget; source recipe is one known positive. Other relevant recipes are unjudged. This is a synthetic reconstruction benchmark, not human relevance evaluation.','shortlist':'API uses rule preselection up to 128; keyword baseline scores all eligible recipes','summary':summary,'queries':queries,'per_query':results}
    (ROOT/'evaluation/results/retrieval_metrics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    ids={json.loads(line)['recipe_id'] for line in (ROOT/'data/processed/foodcom_starter.jsonl').read_text().splitlines()}
    recipes_all=[r for r in main.read_recipes() if r['recipe_id'] in ids]
    evaluate()
