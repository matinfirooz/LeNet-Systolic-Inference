"""Train on 54,000 images, select by 6,000 validation images, evaluate official test once."""
import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from software.data import download,load_idx,split_indices
from software.model import LeNet,prepare_pixels

def evaluate(model,x,y,batch=512):
    model.eval();loss=correct=0;parts=[]
    with torch.inference_mode():
        for begin in range(0,len(y),batch):
            logits=model(x[begin:begin+batch]);target=y[begin:begin+batch]
            loss+=torch.nn.functional.cross_entropy(logits,target,reduction='sum').item()
            correct+=(logits.argmax(1)==target).sum().item();parts.append(logits.numpy())
    return {'n':len(y),'correct':correct,'accuracy':correct/len(y),'cross_entropy':loss/len(y)},np.concatenate(parts)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--epochs',type=int,default=20);parser.add_argument('--threads',type=int,default=4);args=parser.parse_args()
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    torch.manual_seed(7);np.random.seed(7);torch.use_deterministic_algorithms(True)
    download(ROOT/'data/fashion');raw,labels=load_idx(ROOT/'data/fashion');ti,vi=split_indices(labels)
    np.savez(ROOT/'results/software/split_indices.npz',train=ti,validation=vi)
    allx=prepare_pixels(raw);ally=torch.tensor(labels,dtype=torch.long)
    x,y=allx[ti],ally[ti];vx,vy=allx[vi],ally[vi]
    model=LeNet();count=sum(p.numel() for p in model.parameters());assert count==61706
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    scheduler=torch.optim.lr_scheduler.MultiStepLR(optimizer,milestones=[10,16],gamma=.5)
    rng=torch.Generator().manual_seed(42);history=[];best=float('inf');best_epoch=0;started=perf_counter()
    for epoch in range(1,args.epochs+1):
        mark=perf_counter();model.train();loss=correct=0;order=torch.randperm(len(y),generator=rng)
        for begin in range(0,len(y),256):
            idx=order[begin:begin+256];optimizer.zero_grad(set_to_none=True)
            logits=model(x[idx]);value=torch.nn.functional.cross_entropy(logits,y[idx]);value.backward();optimizer.step()
            loss+=value.item()*len(idx);correct+=(logits.detach().argmax(1)==y[idx]).sum().item()
        val,_=evaluate(model,vx,vy)
        record={'epoch':epoch,'train_cross_entropy':loss/len(y),'train_accuracy':correct/len(y),'validation_cross_entropy':val['cross_entropy'],'validation_accuracy':val['accuracy'],'learning_rate':optimizer.param_groups[0]['lr'],'seconds':perf_counter()-mark}
        history.append(record)
        if val['cross_entropy']<best:
            best=val['cross_entropy'];best_epoch=epoch
            torch.save({'state_dict':model.state_dict(),'author':'Matin Firoozbakht','github':'https://github.com/matinfirooz','epoch':epoch,'architecture':'32x32 -> C1/S2/C3/S4/C5/F6/F7'},ROOT/'software/lenet_fashion_mnist.pt')
        scheduler.step();print(json.dumps(record),flush=True)
        (ROOT/'results/software/training_history.json').write_text(json.dumps(history,indent=2))
    checkpoint=torch.load(ROOT/'software/lenet_fashion_mnist.pt',map_location='cpu',weights_only=True);model.load_state_dict(checkpoint['state_dict'])
    np.savez_compressed(ROOT/'software/trained_weights.npz',**{k:v.detach().numpy() for k,v in model.state_dict().items()})
    test_raw,test_labels=load_idx(ROOT/'data/fashion','t10k');test_x=prepare_pixels(test_raw);test_y=torch.tensor(test_labels,dtype=torch.long)
    test,logits=evaluate(model,test_x,test_y);validation,_=evaluate(model,vx,vy)
    np.savez_compressed(ROOT/'results/software/float_test_outputs.npz',logits=logits,labels=test_labels,predictions=logits.argmax(1))
    with (ROOT/'results/software/training_history.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(history[0]));writer.writeheader();writer.writerows(history)
    result={'status':'completed','author':'Matin Firoozbakht','github':'https://github.com/matinfirooz','parameters':count,'train_images':len(ti),'validation_images':len(vi),'test':test,'validation':validation,'best_epoch':best_epoch,'epochs_completed':args.epochs,'training_seconds':perf_counter()-started,'torch_version':torch.__version__,'numpy_version':np.__version__,'python_version':platform.python_version(),'cpu_threads':args.threads,'seed':7,'split_seed':42,'device':'cpu','configuration':{'batch_size':256,'optimizer':'AdamW','learning_rate':.001,'weight_decay':.0001,'activation':'tanh after every convolution, pool, and F6','normalization':'pixel/255; two-pixel zero border'},'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['software/model.py','software/data.py','scripts/train.py']}}
    (ROOT/'results/software/training_summary.json').write_text(json.dumps(result,indent=2));print('FINAL',json.dumps(result),flush=True)

if __name__=='__main__':main()
