"""Batch-one CPU latency with warm-up, eval mode and no background training."""
import argparse,json,platform,sys
from pathlib import Path
from time import perf_counter_ns
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from software.data import load_idx
from software.model import LeNet,prepare_pixels

def main():
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,default=1);p.add_argument('--repeats',type=int,default=500);a=p.parse_args()
    torch.set_num_threads(a.threads);torch.set_num_interop_threads(1)
    m=LeNet();m.load_state_dict(torch.load(ROOT/'software/lenet_fashion_mnist.pt',map_location='cpu',weights_only=True)['state_dict']);m.eval()
    raw,_=load_idx(ROOT/'data/fashion','t10k');x=prepare_pixels(raw[:100])
    records={}
    with torch.inference_mode():
        for mode in ['model_only','normalize_pad_model']:
            for i in range(100):torch.softmax(m(x[i%100:i%100+1]),1)
            times=[]
            for i in range(a.repeats):
                j=i%100;start=perf_counter_ns()
                sample=x[j:j+1] if mode=='model_only' else prepare_pixels(raw[j:j+1])
                torch.softmax(m(sample),1)
                times.append((perf_counter_ns()-start)/1e6)
            records[mode]={'mean_ms':float(np.mean(times)),'median_ms':float(np.median(times)),'p5_ms':float(np.percentile(times,5)),'p95_ms':float(np.percentile(times,95)),'samples_ms':times}
    cpu='unknown'
    if Path('/proc/cpuinfo').exists():
        cpu=next((s.split(':',1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),'unknown')
    result={'status':'measured','device':'cpu','cpu':cpu,'threads':a.threads,'batch_size':1,'warmup_calls':100,'timed_calls_per_mode':a.repeats,'torch_version':torch.__version__,'python_version':platform.python_version(),'includes_softmax':True,'results':records}
    (ROOT/'results/software/benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='results'}));print({k:{n:v for n,v in r.items() if n!='samples_ms'} for k,r in records.items()})
if __name__=='__main__':main()
