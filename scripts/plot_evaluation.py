"""Render measured CNN confusion matrix and retrieval comparisons."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'evaluation/results/cnn_metrics.json').read_text())
matrix=np.array(report['test']['confusion_matrix']);labels=report['classes']
fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
im=ax.imshow(matrix,cmap='Greens',vmin=0,vmax=250)
for i in range(5):
 for j in range(5):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>125 else '#243c2b')
ax.set_xticks(range(5),labels,rotation=25,ha='right');ax.set_yticks(range(5),labels);ax.set_xlabel('Predicted class');ax.set_ylabel('True class')
ax.set_title('ResNet18 transfer learning: 5-class Food-101\nOfficial held-out test: n=1,250 | accuracy=91.60% | macro F1=0.9165')
fig.colorbar(im,ax=ax,label='Images');fig.savefig(ROOT/'evaluation/results/cnn_confusion_matrix.png',dpi=160);plt.close(fig)
retrieval=json.loads((ROOT/'evaluation/results/retrieval_metrics.json').read_text())['summary']
fig,ax=plt.subplots(figsize=(7,4.5),layout='constrained');names=list(retrieval);x=np.arange(len(names));width=.35
for offset,key,label in [(-width/2,'known_positive_hit_at_3','Known-positive Hit@3'),(width/2,'known_positive_mrr_at_10','Known-positive MRR@10')]:
 bars=ax.bar(x+offset,[retrieval[n][key] for n in names],width,label=label)
 ax.bar_label(bars,fmt='%.2f',padding=3)
ax.set_xticks(x,['Keyword Jaccard','Ingredient rules','Hybrid semantic']);ax.set_ylim(0,1.15);ax.set_title('20 synthetic ingredient queries on 5,000 real recipes\nReconstruction benchmark; no human relevance judgments');ax.legend(loc='upper right');fig.savefig(ROOT/'evaluation/results/retrieval_comparison.png',dpi=160)
