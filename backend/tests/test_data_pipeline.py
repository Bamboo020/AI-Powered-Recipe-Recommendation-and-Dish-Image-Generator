from pathlib import Path
import sys
import json
import sqlite3
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from prepare_foodcom import parse_r_list, minutes
from import_foodcom import import_records


def test_r_vector_parser_does_not_execute_code():
    assert parse_r_list('c("egg", "tomato", NA)') == ['egg','tomato',None]
    assert parse_r_list('"salt"') == ['salt']
    with pytest.raises(ValueError):parse_r_list('__import__("os").system("echo unsafe")')
    assert minutes('PT1H2M3S')==63
    assert minutes('NA') is None


def test_real_import_is_idempotent_and_preserves_unknown_rice(tmp_path):
    row={'recipe_id':'foodcom-42','title':'Fried Rice','source':'test source','source_url':'https://example.com/42','total_minutes':20,'steps':['Cook.'],'ingredient_items':[{'name':'rice','quantity':'2','unit':None},{'name':'eggs','quantity':'1','unit':None}],'data_quality_flags':['ingredients_not_normalized'],'cuisine_tags':[],'servings':None}
    data=tmp_path/'recipes.jsonl';data.write_text(json.dumps(row)+'\n');db=tmp_path/'test.sqlite3'
    assert import_records(data,db)==1
    assert import_records(data,db)==1
    with sqlite3.connect(db) as connection:
        records=connection.execute('SELECT payload FROM recipes').fetchall()
    assert len(records)==1
    imported=json.loads(records[0][0])
    assert imported['ingredient_items'][0]['name']=='rice_unspecified'
    assert imported['ingredient_items'][0]['source_name']=='rice'
    assert imported['ingredient_items'][1]['name']=='egg'
    assert imported['source_url']==row['source_url']
