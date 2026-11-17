"""Transfer learning: frozen ImageNet ResNet18 CNN + trained five-class head.
Select head checkpoint on validation only; evaluate official test exactly once.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision.models import resnet18, ResNet18_Weights
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

class FoodDataset(Dataset):
    def __init__(self,split,transform):
        self.rows=[json.loads(x) for x in (ROOT/f'data/processed/food101/{split}.jsonl').read_text().splitlines()]
        self.transform=transform
    def __len__(self):return len(self.rows)
    def __getitem__(self,index):
        row=self.rows[index]
        with Image.open(ROOT/row['path']) as image:
            tensor=self.transform(image.convert('RGB'))
        return tensor,row['label']


def metrics(logits,targets,labels):
    predicted=logits.argmax(1)
    matrix=torch.zeros(len(labels),len(labels),dtype=torch.int64)
    for t,p in zip(targets.tolist(),predicted.tolist()):matrix[t,p]+=1
    rows=[]
    for i,name in enumerate(labels):
        tp=matrix[i,i].item();precision=tp/max(matrix[:,i].sum().item(),1);recall=tp/max(matrix[i,:].sum().item(),1)
        rows.append({'class':name,'precision':precision,'recall':recall,'f1':2*precision*recall/max(precision+recall,1e-12),'support':int(matrix[i,:].sum())})
    return {'top1_accuracy':float((predicted==targets).float().mean()),'top3_accuracy':float((logits.topk(min(3,len(labels)),dim=1).indices==targets[:,None]).any(1).float().mean()),'macro_f1':sum(r['f1'] for r in rows)/len(rows),'confusion_matrix':matrix.tolist(),'per_class':rows,'count':len(targets)}


def train(epochs,batch_size):
    started=time.monotonic();random.seed(42);torch.manual_seed(42);torch.set_num_threads(4)
    device='mps' if torch.backends.mps.is_available() else 'cpu'
    labels=json.loads((ROOT/'data/processed/food101/labels.json').read_text())
    weights=ResNet18_Weights.DEFAULT
    model=resnet18(weights=weights)
    model.fc=nn.Identity();model.eval().to(device)
    features={}
    for split in ['train','validation','test']:
        loader=DataLoader(FoodDataset(split,weights.transforms()),batch_size=batch_size,shuffle=False,num_workers=0)
        vectors=[];targets=[]
        with torch.inference_mode():
            for index,(images,y) in enumerate(loader):
                vectors.append(model(images.to(device)).cpu());targets.append(y)
                if index%15==0:print(f'{split}: extracted {min((index+1)*batch_size,len(loader.dataset))}/{len(loader.dataset)}',flush=True)
        features[split]=(torch.cat(vectors).clone(),torch.cat(targets).clone())
    # Classifier head trains on CPU from fixed CNN features; no test labels in selection.
    head=nn.Linear(512,len(labels));optimizer=torch.optim.AdamW(head.parameters(),lr=.003,weight_decay=.01)
    history=[];best=-1.;best_state=None
    x,y=features['train'];vx,vy=features['validation']
    for epoch in range(epochs):
        head.train();order=torch.randperm(len(y));loss_total=0
        for indices in order.split(128):
            optimizer.zero_grad();loss=nn.functional.cross_entropy(head(x[indices]),y[indices]);loss.backward();optimizer.step();loss_total+=loss.item()*len(indices)
        head.eval()
        with torch.inference_mode():validation=metrics(head(vx),vy,labels)
        row={'epoch':epoch+1,'train_loss':loss_total/len(y),'validation_accuracy':validation['top1_accuracy'],'validation_macro_f1':validation['macro_f1']}
        history.append(row)
        if validation['macro_f1']>best:
            best=validation['macro_f1'];best_state={k:v.detach().clone() for k,v in head.state_dict().items()}
        if epoch%10==0:print(json.dumps(row),flush=True)
    head.load_state_dict(best_state);head.eval()
    with torch.inference_mode():
        validation=metrics(head(vx),vy,labels)
        tx,ty=features['test'];test_logits=head(tx);test=metrics(test_logits,ty,labels)
    model.to('cpu');model.fc=head
    assets=ROOT/'model_assets/food101_5class';assets.mkdir(parents=True,exist_ok=True)
    checkpoint=assets/'resnet18.pt';torch.save(model.state_dict(),checkpoint)
    (assets/'labels.json').write_text(json.dumps(labels,indent=2)+'\n')
    report={'model':'ResNet18 ImageNet pretrained backbone + trained linear head','training_scope':'backbone frozen; only 512-to-5 classifier head trained','device_for_feature_extraction':device,'seed':42,'epochs':epochs,'selection':'highest validation macro F1; no test-based tuning','classes':labels,'train_count':len(y),'validation':validation,'test':test,'majority_baseline_accuracy':1/len(labels),'history':history,'seconds':round(time.monotonic()-started,2),'checkpoint_sha256':hashlib.file_digest(checkpoint.open('rb'),'sha256').hexdigest(),'data_manifest':json.loads((ROOT/'data/processed/food101/manifest.json').read_text()),'torch_version':torch.__version__,'limitations':['Supported five classes only; closed-set test excludes unknown dishes','No calibrated confidence or open-set rejection','Feature extraction uses fixed ImageNet preprocessing; no end-to-end fine-tuning']}
    results=ROOT/'evaluation/results';results.mkdir(exist_ok=True)
    (results/'cnn_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    predictions=[]
    rows=[json.loads(line) for line in (ROOT/'data/processed/food101/test.jsonl').read_text().splitlines()]
    for row,logits in zip(rows,test_logits):predictions.append({**row,'predicted_label':int(logits.argmax()),'probabilities':logits.softmax(0).tolist()})
    (ROOT/'data/processed/food101/test_predictions.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in predictions))
    print(json.dumps({k:v for k,v in report.items() if k not in ['history','data_manifest']},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--epochs',type=int,default=60);parser.add_argument('--batch-size',type=int,default=32);args=parser.parse_args();train(args.epochs,args.batch_size)
