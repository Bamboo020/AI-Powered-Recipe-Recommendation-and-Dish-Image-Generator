"""Refresh only nutrition for existing prepared records; preserve selection and aliases."""
import csv
import json
import sqlite3
from prepare_foodcom import ROOT, source_nutrition


def main():
    paths = [ROOT/'data/processed/foodcom_starter.jsonl', ROOT/'data/processed/foodcom_photo_extension.jsonl']
    groups = [[json.loads(line) for line in path.read_text().splitlines()] for path in paths]
    ids = {r['recipe_id'] for group in groups for r in group}
    nutrition = {}
    with (ROOT/'data/raw/foodcom/recipes.csv').open(newline='', encoding='utf-8-sig') as source:
        for row in csv.DictReader(source):
            key = 'foodcom-'+row['RecipeId']
            if key in ids:
                nutrition[key] = source_nutrition(row)
            if len(nutrition) == len(ids):
                break
    if len(nutrition) != len(ids):
        raise ValueError('Missing source records; no files updated')
    for path, group in zip(paths, groups):
        for record in group:
            record['nutrition'] = nutrition[record['recipe_id']]
        path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in group))
    with sqlite3.connect(ROOT/'recipes.sqlite3') as connection:
        for key, payload in connection.execute('SELECT recipe_id, payload FROM recipes').fetchall():
            if key in nutrition:
                record = json.loads(payload)
                record['nutrition'] = nutrition[key]
                connection.execute('UPDATE recipes SET payload=? WHERE recipe_id=?', (json.dumps(record), key))
    print(f'Updated source nutrition for {len(nutrition)} recipes; serving basis remains unverified.')


if __name__ == '__main__':
    main()
