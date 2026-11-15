"""Export every trained parameter and evaluate the integer network on 10,000 test images."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from software.data import load_idx
from software.fixed_point import quantize,infer_integer,write_hex,LAYERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--rtl-images',type=int,default=16);args=p.parse_args()
    weights=dict(np.load(ROOT/'software/trained_weights.npz'));q,clips=quantize(weights)
    np.savez_compressed(ROOT/'software/integer_weights.npz',**q)
    allw=np.concatenate([q[name+'.weight'].reshape(-1) for name,*_ in LAYERS]);allb=np.concatenate([q[name+'.bias'] for name,*_ in LAYERS])
    assert len(allw)==61470 and len(allb)==236
    mem=ROOT/'hardware/mem';write_hex(mem/'weights.hex',allw,16);write_hex(mem/'biases.hex',allb,48)
    write_hex(mem/'tanh.hex',q['tanh_lut'],16);write_hex(mem/'exp.hex',q['exp_lut'],32)
    with (ROOT/'results/software/parameters.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['tensor','index','floating_value','integer_value','fractional_bits','memory_address'])
        wb=bb=0
        for name,*_ in LAYERS:
            for suffix,frac in [('weight',12),('bias',24)]:
                key=name+'.'+suffix;base=wb if frac==12 else bb
                for i,(f,v) in enumerate(zip(weights[key].reshape(-1),q[key].reshape(-1))):writer.writerow([key,i,format(float(f),'.9g'),int(v),frac,base+i])
                if frac==12:wb+=q[key].size
                else:bb+=q[key].size
    raw,labels=load_idx(ROOT/'data/fashion','t10k');saved=np.load(ROOT/'results/software/float_test_outputs.npz')
    results=[];started=perf_counter()
    for begin in range(0,len(raw),64):
        out=infer_integer(raw[begin:begin+64],q);results.append(out)
        if begin%1024==0:print('Integer evaluation',begin,'/',len(raw),flush=True)
    merged={key:np.concatenate([x[key] for x in results]) for key in results[0]}
    elapsed=perf_counter()-started;pred=merged['predictions'];float_pred=saved['predictions']
    correct=int(np.count_nonzero(pred==labels));disagreements=int(np.count_nonzero(pred!=float_pred))
    np.savez_compressed(ROOT/'results/software/integer_test_outputs.npz',**merged,labels=labels)
    n=min(args.rtl_images,len(raw));reference=infer_integer(raw[:n],q,True)
    per_image=mem/'reference';per_image.mkdir(exist_ok=True)
    for i in range(n):
        write_hex(per_image/f'trace_{i:05d}.hex',reference['trace'][i],16)
        write_hex(per_image/f'logits_{i:05d}.hex',reference['logits'][i],48)
        write_hex(per_image/f'probabilities_{i:05d}.hex',reference['probabilities'][i],16)
    write_hex(mem/'reference_trace.hex',reference['trace'],16);write_hex(mem/'reference_logits.hex',reference['logits'],48)
    write_hex(mem/'reference_probabilities.hex',reference['probabilities'],16);write_hex(mem/'reference_predictions.hex',reference['predictions'],8)
    write_hex(mem/'test_indices.hex',np.arange(n),32)
    with (ROOT/'results/software/test_predictions.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['test_index','label','floating_prediction','integer_prediction','integer_correct'])
        wr.writerows(zip(range(len(raw)),labels.astype(int),float_pred.astype(int),pred.astype(int),(pred==labels).astype(int)))
    bounds=[]
    for name,*_ in LAYERS:
        bound=np.abs(q[name+'.weight']).reshape(q[name+'.weight'].shape[0],-1).sum(1)*4096+np.abs(q[name+'.bias'])
        assert np.all(bound<(1<<47));bounds.append({'layer':name,'maximum_accumulator_bound':int(bound.max()),'fits_signed_48':True})
    result={'status':'completed','n_test':len(labels),'correct':correct,'accuracy':correct/len(labels),'floating_correct':int(np.count_nonzero(float_pred==labels)),'floating_integer_disagreements':disagreements,'prediction_agreement':1-disagreements/len(labels),'weight_bias_clips':clips,'evaluation_seconds':elapsed,'rtl_reference_images':n,'rtl_test_indices':list(range(n)),'fixed_point':{'weight_bits':16,'activation_bits':16,'fractional_bits':12,'accumulator_bits':48,'accumulator_fractional_bits':24,'tanh_entries':4097,'tanh_grid_step':1/256,'exp_entries':4097,'probability_bits':16,'probability_fractional_bits':16},'accumulator_bounds':bounds,'hex_sha256':{str(p.relative_to(mem)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(mem.rglob('*.hex'))}}
    (ROOT/'results/software/quantization.json').write_text(json.dumps(result,indent=2));print('FINAL',json.dumps(result),flush=True)
if __name__=='__main__':main()
