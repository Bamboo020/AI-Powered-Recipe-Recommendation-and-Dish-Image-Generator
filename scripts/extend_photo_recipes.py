"""Add source-backed category coverage; heuristics are documented, not paired image IDs."""
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.dishes import matches_dish,DISH_PATTERNS
from prepare_foodcom import parse_r_list,minutes

counts={k:0 for k in DISH_PATTERNS}
pinfile=ROOT/'data_metadata/photo_extension_ids.json'
pinned=set(json.loads(pinfile.read_text())) if pinfile.exists() else None
existing={json.loads(x)['recipe_id'] for x in (ROOT/'data/processed/foodcom_starter.jsonl').read_text().splitlines()}
new=[]
with (ROOT/'data/raw/foodcom/recipes.csv').open(newline='',encoding='utf-8-sig') as source:
    for row in csv.DictReader(source):
        if pinned and len(new)>=len(pinned):break
        if not pinned and all(v>=30 for v in counts.values()):break
        if pinned and row['RecipeId'] not in pinned:continue
        duration=minutes(row['TotalTime'])
        if not duration or duration>120:continue
        try:
            record={'recipe_id':'foodcom-'+row['RecipeId'],'title':row['Name'],'source_category':row['RecipeCategory'],'source_keywords':parse_r_list(row['Keywords'])}
            categories=[c for c in counts if counts[c]<30 and matches_dish(record,c)]
            if not categories and not pinned:continue
            ingredients=parse_r_list(row['RecipeIngredientParts']);quantities=parse_r_list(row['RecipeIngredientQuantities']);steps=parse_r_list(row['RecipeInstructions'])
            if not ingredients or len(ingredients)>25 or any(not x for x in ingredients) or not steps or any(not x for x in steps):continue
        except ValueError:continue
        for c in categories:counts[c]+=1
        if record['recipe_id'] in existing:continue
        record.update(source='Food.com via Kaggle irkaal/foodcom-recipes-and-reviews',source_dataset_id=row['RecipeId'],source_url='https://www.food.com/recipe/'+row['RecipeId'],total_minutes=duration,servings=int(row['RecipeServings']) if row['RecipeServings'].isdigit() else None,ingredient_items=[{'name':name,'quantity':quantities[i] if i<len(quantities) else None,'unit':None} for i,name in enumerate(ingredients)],steps=steps,cuisine_tags=[],data_quality_flags=['ingredients_not_normalized','units_not_separated','cuisine_not_inferred','category_mapping_heuristic','source_url_constructed_not_live_verified','not_independently_reviewed'])
        new.append(record);existing.add(record['recipe_id'])
output=ROOT/'data/processed/foodcom_photo_extension.jsonl';output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in new))
(ROOT/'evaluation/results/category_coverage.json').write_text(json.dumps({'selection':'Pinned source IDs in data_metadata/photo_extension_ids.json preserve the original category-coverage sample (0<minutes<=120, <=25 ingredients). Current mapping may exclude some pinned records at recommendation time.','eligible_extension_counts_current_mapping':counts,'new_records':len(new),'limitations':'Category mapping is heuristic and not a paired Food101/Food.com annotation.'},indent=2)+'\n')
print(counts,len(new),flush=True)
