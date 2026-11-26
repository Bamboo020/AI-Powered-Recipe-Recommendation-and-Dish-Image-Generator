"""Import a provenance-preserving prepared JSONL into the application SQLite DB."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.main import DB_PATH, normalize


def import_records(path,db):
    inserted=0
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS recipes (recipe_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        for line in path.open():
            record=json.loads(line)
            if not record['recipe_id'].startswith('foodcom-') or not record['steps'] or not record['ingredient_items'] or not isinstance(record['total_minutes'],int) or record['total_minutes']<=0:
                raise ValueError('Invalid real recipe record')
            for item in record['ingredient_items']:
                item['source_name']=item['name']
                if item['name'].strip().lower() == 'rice':
                    item['name']='rice_unspecified'
                    if 'rice_state_unspecified' not in record['data_quality_flags']: record['data_quality_flags'].append('rice_state_unspecified')
                else:
                    item['name']=normalize(item['name'])
            record['data_quality_flags']=[f for f in record['data_quality_flags'] if f!='ingredients_not_normalized']+['limited_alias_normalization']
            connection.execute('INSERT INTO recipes VALUES (?,?) ON CONFLICT(recipe_id) DO UPDATE SET payload=excluded.payload',(record['recipe_id'],json.dumps(record,ensure_ascii=False)))
            inserted+=1
    print(json.dumps({'imported':inserted,'database':str(db),'source':str(path)}))
    return inserted

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,default=ROOT/'data/processed/foodcom_starter.jsonl');parser.add_argument('--db',type=Path,default=DB_PATH);args=parser.parse_args();import_records(args.input,args.db)
