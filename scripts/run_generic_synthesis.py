"""Yosys process/memory synthesis and connectivity, without device mapping or timing."""
import argparse,hashlib,importlib.metadata,json,os,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/hardware/generic'

def one(top,cache):
    from pyosys import libyosys as ys
    os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True);label=top+f'_cache{cache}'
    source=(ROOT/'hardware/rtl/files.f').read_text().splitlines();design=ys.Design()
    commands=['read_verilog -sv -DSYNTHESIS '+' '.join(source)]
    if top.startswith('lenet_top_'):commands.append(f'chparam -set CACHE_ENABLE {cache} {top}')
    commands += [f'hierarchy -check -top {top}','proc','opt','wreduce','opt','check -assert','memory_dff','memory_collect','opt_clean','check -assert',f'tee -o results/hardware/generic/{label}_statistics.json stat -json',f'write_json results/hardware/generic/{label}_netlist.json']
    for command in commands:ys.run_pass(command,design)
    path=OUT/(label+'_netlist.json');net=json.loads(path.read_text());modules=net['modules'];counts=Counter();pe_mul=[]
    def expand(mod,prefix):
        for name,cell in modules[mod].get('cells',{}).items():
            child=cell['type'];location=prefix+'/'+name
            if child in modules:expand(child,location)
            else:
                counts[child]+=1
                if child=='$mul' and 'u_pe/' in location:
                    pe_mul.append({'instance':location,'a_bits':int(cell['parameters']['A_WIDTH'],2),'b_bits':int(cell['parameters']['B_WIDTH'],2)})
    expand(top,top)
    assert len(pe_mul)==25 and all(m['a_bits']==16 and m['b_bits']==16 for m in pe_mul)
    assert not any('latch' in key for key in counts)
    result={'top':top,'cache_enable':cache,'status':'passed','generic_leaf_cells':dict(counts),'compute_pe_multipliers':pe_mul,'generic_memories':counts.get('$mem_v2',0),'inferred_latches':0,'netlist':str(path.relative_to(ROOT))}
    (OUT/(label+'_result.json')).write_text(json.dumps(result,indent=2));print('PASS generic',top,'cache',cache)

def main():
    p=argparse.ArgumentParser();p.add_argument('--one');p.add_argument('--cache',type=int,default=0);a=p.parse_args()
    if a.one:one(a.one,a.cache);return
    OUT.mkdir(parents=True,exist_ok=True);configs=[(f'sa_{m}_5x5',0) for m in ['ws','os','is']]+[(f'lenet_top_{m}',c) for m in ['ws','os','is'] for c in [0,1]];rows=[]
    for top,cache in configs:
        label=top+f'_cache{cache}'
        with (OUT/(label+'.log')).open('w') as f:subprocess.run([sys.executable,__file__,'--one',top,'--cache',str(cache)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        rows.append(json.loads((OUT/(label+'_result.json')).read_text()));print('Checked',label,flush=True)
    tracked=sorted((ROOT/'hardware/rtl').glob('*'))+sorted((ROOT/'hardware/mem').glob('*.hex'))
    result={'status':'passed','tool':'Yosys via Pyosys','version':importlib.metadata.version('pyosys'),'scope':'Technology-independent process/memory synthesis and connectivity only; FPGA utilization, timing and power are unmeasured.','cases':rows,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked if p.is_file()},'mapped_DSPs':None,'mapped_LUTs':None,'routed_clock_MHz':None,'power_watts':None}
    (ROOT/'results/hardware/generic_synthesis.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
