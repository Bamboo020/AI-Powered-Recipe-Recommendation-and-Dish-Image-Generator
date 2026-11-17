"""Extract supported classes and preserve official test membership."""
import hashlib
import json
from pathlib import Path
import random
import tarfile

ROOT=Path(__file__).resolve().parents[1]
CLASSES=['dumplings','fried_rice','omelette','pizza','ramen']


def prepare():
    archive=ROOT/'data/raw/food-101.tar.gz'
    output=ROOT/'data/raw/food101'
    output.mkdir(parents=True,exist_ok=True)
    extracted=0
    with tarfile.open(archive,'r:gz') as bundle:
        for member in bundle:
            parts=Path(member.name).parts
            wanted=(len(parts)>=3 and parts[0]=='food-101' and (parts[1]=='meta' or (parts[1]=='images' and parts[2] in CLASSES)))
            if wanted and member.isfile():
                bundle.extract(member,output,filter='data')
                extracted+=1
    base=output/'food-101'
    train=(base/'meta/train.txt').read_text().splitlines()
    test=(base/'meta/test.txt').read_text().splitlines()
    split={'train':[],'validation':[],'test':[]}
    for label,name in enumerate(CLASSES):
        rows=sorted(x for x in train if x.startswith(name+'/'))
        official_test=sorted(x for x in test if x.startswith(name+'/'))
        assert len(rows)==750 and len(official_test)==250
        random.Random(42).shuffle(rows)
        for key,values in [('train',rows[:600]),('validation',rows[600:]),('test',official_test)]:
            for image_id in values:
                path=base/'images'/(image_id+'.jpg')
                if not path.is_file():raise FileNotFoundError(path)
                split[key].append({'image_id':image_id,'path':str(path.relative_to(ROOT)),'label':label,'class_name':name})
    memberships=[{r['image_id'] for r in rows} for rows in split.values()]
    assert all(not memberships[i]&memberships[j] for i in range(3) for j in range(i+1,3))
    processed=ROOT/'data/processed/food101'
    processed.mkdir(parents=True,exist_ok=True)
    for key,rows in split.items():
        (processed/(key+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (processed/'labels.json').write_text(json.dumps(CLASSES,indent=2)+'\n')
    manifest={'source':'https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/','classes':CLASSES,'counts':{k:len(v) for k,v in split.items()},'seed':42,'split_policy':'600 train / 150 validation from official 750 train per class; all 250 official test per class held out','extracted_files':extracted,'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()}
    (processed/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest),flush=True)

if __name__=='__main__':prepare()
