"""Prepare real Food.com records from irkaal's archive, without eval or invented fields."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|NA')


def source_nutrition(row):
    import math
    values = {}
    for key, column in [('calories_kcal', 'Calories'), ('protein_g', 'ProteinContent'), ('carbohydrate_g', 'CarbohydrateContent'), ('fat_g', 'FatContent'), ('fiber_g', 'FiberContent')]:
        try:
            number = float(row.get(column, ''))
            values[key] = number if math.isfinite(number) and number >= 0 else None
        except (TypeError, ValueError):
            values[key] = None
    return {**values, 'basis': 'source_reported_basis_unverified', 'note': 'Original dataset values. Per-serving basis has not been verified; do not divide, rescale or treat as a personal calorie target.'}


def parse_r_list(value):
    value = value.strip()
    if value in ('NA', '', 'character(0)', 'c()'):
        return []
    if value.startswith('c(') and value.endswith(')'):
        value = value[2:-1].strip()
    matches = list(TOKEN.finditer(value))
    cursor = 0
    result = []
    for match in matches:
        gap = value[cursor:match.start()].strip()
        if gap not in ('', ',') or (cursor and gap != ','):
            raise ValueError('Malformed R vector')
        token = match.group()
        result.append(None if token == 'NA' else json.loads(token.replace("\\'", "'")))
        cursor = match.end()
    if value[cursor:].strip() or not matches:
        raise ValueError('Malformed R vector')
    return result


def minutes(value):
    match = re.fullmatch(r'PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?', value)
    if not match or not any(match.groups()):
        return None
    hours, mins, seconds = (float(v or 0) for v in match.groups())
    import math
    return math.ceil(hours*60+mins+seconds/60)


def prepare(archive, limit):
    raw = ROOT / 'data/raw/foodcom'
    processed = ROOT / 'data/processed'
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        # Extract only named CSVs; never extract arbitrary archive paths.
        for name in ('recipes.csv', 'reviews.csv'):
            target = raw / name
            if not target.exists() or target.stat().st_size != bundle.getinfo(name).file_size:
                with bundle.open(name) as source, target.open('wb') as destination:
                    import shutil
                    shutil.copyfileobj(source, destination)
    count = selected = rejected = 0
    ids = set()
    fields = []
    examples = processed / 'foodcom_starter.jsonl'
    with (raw/'recipes.csv').open(newline='', encoding='utf-8-sig') as source, examples.open('w') as output:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        for row in reader:
            count += 1
            if selected >= limit:
                continue
            duration = minutes(row['TotalTime'])
            if not row['RecipeId'].isdigit() or row['RecipeId'] in ids or not duration or duration > 120:
                continue
            try:
                ingredients = parse_r_list(row['RecipeIngredientParts'])
                quantities = parse_r_list(row['RecipeIngredientQuantities'])
                steps = parse_r_list(row['RecipeInstructions'])
                tags = parse_r_list(row['Keywords'])
            except (ValueError, json.JSONDecodeError):
                rejected += 1
                continue
            if not ingredients or len(ingredients) > 15 or any(not x for x in ingredients) or not steps or any(not x for x in steps):
                continue
            servings = int(row['RecipeServings']) if row['RecipeServings'].isdigit() else None
            record = {
                'recipe_id': 'foodcom-'+row['RecipeId'],
                'source': 'Food.com via Kaggle irkaal/foodcom-recipes-and-reviews',
                'source_dataset_id': row['RecipeId'],
                'source_url': 'https://www.food.com/recipe/'+row['RecipeId'],
                'title': row['Name'], 'total_minutes': duration, 'servings': servings,
                'ingredient_items': [{'name': name, 'quantity': quantities[i] if i<len(quantities) else None, 'unit': None} for i,name in enumerate(ingredients)],
                'steps': steps, 'cuisine_tags': [], 'source_category': row['RecipeCategory'],
                'source_keywords': tags,
                'nutrition': source_nutrition(row),
                'data_quality_flags': ['ingredients_not_normalized', 'units_not_separated', 'cuisine_not_inferred', 'source_url_constructed_not_live_verified', 'not_independently_reviewed'] + (['servings_missing'] if servings is None else [])
            }
            output.write(json.dumps(record,ensure_ascii=False)+'\n')
            ids.add(row['RecipeId']);selected+=1
    with (raw/'reviews.csv').open(newline='',encoding='utf-8-sig') as source:
        reader = csv.DictReader(source)
        review_fields = reader.fieldnames
        reviews_count=sum(1 for _ in reader)
    report={'dataset':'irkaal/foodcom-recipes-and-reviews','recipe_rows':count,'review_rows':reviews_count,'starter_rows':selected,'parse_rejections_while_selecting':rejected,'starter_selection':'First valid unique records in source order, positive known TotalTime <=120 min and <=15 ingredients; not a random evaluation sample','recipe_fields':fields,'review_fields':review_fields,'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()}
    (processed/'foodcom_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,default=ROOT/'data/raw/foodcom-recipes-and-reviews.zip')
    parser.add_argument('--limit',type=int,default=5000)
    args=parser.parse_args()
    prepare(args.archive,args.limit)
