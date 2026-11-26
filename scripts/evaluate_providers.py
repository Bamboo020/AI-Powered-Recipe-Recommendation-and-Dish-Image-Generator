"""Small real-provider smoke and latency study; not a factuality/quality benchmark."""
import json
from pathlib import Path
import time
import httpx
ROOT=Path(__file__).resolve().parents[1]
cases=[]
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=120.) as client:
    for recipe_id in ['foodcom-11042','foodcom-8709','foodcom-9128']:
        started=time.monotonic();response=client.post('/api/explain',json={'recipe_id':recipe_id});data=response.json()
        cases.append({'recipe_id':recipe_id,'http_status':response.status_code,'seconds':round(time.monotonic()-started,2),'used_llm':data.get('is_llm_generated',False),'source_linkage_correct':data.get('source_recipe_id')==recipe_id,'explanation':data.get('text')})
        print(json.dumps(cases[-1],ensure_ascii=False),flush=True)
old=json.loads((ROOT/'output/local-ai-smoke.json').read_text())
diffusion=[{'sample':'initial_prompt','recipe_id':'demo-002','seconds':old['diffusion']['seconds'],'completed':old['diffusion']['response']['status']=='completed','file':old['diffusion']['response']['url'],'visual_review_by':'coding assistant, not independent human study','visual_review':'Plated tomato and fried egg, no recognizable fried rice. Dish mismatch.'}, {'sample':'english_description','recipe_id':'demo-002','seconds':old['diffusion_refined_prompt']['seconds'],'completed':old['diffusion_refined_prompt']['response']['status']=='completed','file':old['diffusion_refined_prompt']['response']['url'],'visual_review_by':'coding assistant, not independent human study','visual_review':'Rice dish recognizable, but fried egg and additional green vegetables differ from the source scrambled-egg recipe. Partial match.'}]
report={'llm':{'model':'qwen2.5:7b','cases':cases,'success_rate':sum(x['used_llm'] for x in cases)/len(cases),'mean_seconds':sum(x['seconds'] for x in cases)/len(cases),'limitations':'Three source-grounded calls only. Linkage checks metadata, not factual consistency. Independent human factuality ratings are pending.'},'diffusion':{'model':'runwayml/stable-diffusion-v1-5','cases':diffusion,'technical_success_rate':sum(x['completed'] for x in diffusion)/len(diffusion),'mean_seconds':sum(x['seconds'] for x in diffusion)/len(diffusion),'limitations':'Two sequential development images of one illustrative dish; prompt changed after first image. Not an independent or representative quality benchmark. Extra visual ingredients remain.'}}
(ROOT/'evaluation/results/provider_smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
