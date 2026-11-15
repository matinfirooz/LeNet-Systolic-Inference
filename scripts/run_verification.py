"""Actual Icarus regressions for all dataflows, memory modes and protocol corners."""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/hardware';BUILD=OUT/'build'

def toolchain():
    iv=os.environ.get('IVERILOG') or shutil.which('iverilog');vv=os.environ.get('VVP') or shutil.which('vvp');base=os.environ.get('IVL_BASE')
    private=ROOT.parents[1]/'tmp/iverilog_tools/usr'
    if not iv and (private/'bin/iverilog').exists():iv=str(private/'bin/iverilog');vv=str(private/'bin/vvp');base=str(private/'lib/x86_64-linux-gnu/ivl')
    if not iv or not vv:raise RuntimeError('Install Icarus Verilog or set IVERILOG, VVP and optionally IVL_BASE.')
    return iv,vv,base

def run_case(name,bench,params,plusargs):
    iv,vv,base=toolchain();target=BUILD/(name+'.vvp');cmd=[iv]+(['-B',base] if base else [])+['-g2012','-s',bench]
    cmd += [f'-P{bench}.{k}={v}' for k,v in params.items()]
    cmd += ['-o',str(target),'-c','hardware/rtl/files.f',f'hardware/tb/{bench}.sv']
    compile_result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'_compile.log')).write_text(compile_result.stdout+compile_result.stderr)
    compile_result.check_returncode();started=perf_counter()
    result=subprocess.run([vv,str(target),*plusargs],cwd=ROOT,capture_output=True,text=True)
    elapsed=perf_counter()-started;log=result.stdout+result.stderr;(OUT/(name+'.log')).write_text(log)
    if result.returncode or 'FATAL' in log or 'PASS ' not in log:raise RuntimeError(name+' failed; see '+name+'.log')
    frames=[]
    for line in log.splitlines():
        if line.startswith('FRAME '):frames.append({k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)})
    return {'name':name,'bench':bench,'parameters':params,'status':'passed','wall_seconds':elapsed,'frames':frames,'log':f'results/hardware/{name}.log','pass_messages':[line for line in log.splitlines() if line.startswith('PASS ')]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=16);p.add_argument('--jobs',type=int,default=3);p.add_argument('--units-only',action='store_true');p.add_argument('--networks-only',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);BUILD.mkdir(exist_ok=True)
    q=json.loads((ROOT/'results/software/quantization.json').read_text());max_images=q['rtl_reference_images']
    if args.samples>max_images:raise ValueError('Generate enough reference images with scripts/export_evaluate.py --rtl-images N first.')
    cases=[]
    if not args.networks_only:
        cases += [('arrays','tb_arrays',{},[]),('memory_direct','tb_weight_memory',{'CACHE_ENABLE':0},[]),('memory_cache','tb_weight_memory',{'CACHE_ENABLE':1},[]),('numerics','tb_numerics',{},[]),('softmax','tb_softmax',{},[])]
    if not args.units_only:
        for df,label in enumerate(['ws','os','is']):
            for cache in [0,1]:cases.append((f'lenet_{label}_cache{cache}','tb_lenet',{'DATAFLOW':df,'CACHE_ENABLE':cache,'MAX_IMAGES':max_images},[f'+N={args.samples}']))
        cases.append(('protocol_reset_stalls','tb_lenet',{'DATAFLOW':0,'CACHE_ENABLE':1,'STALLS':1,'RESET_TEST':1,'MAX_IMAGES':max_images},['+N=1']))
    paths=sorted((ROOT/'hardware/rtl').glob('*'))+sorted((ROOT/'hardware/tb').glob('*.sv'))+sorted((ROOT/'hardware/mem').rglob('*.hex'))+[ROOT/'software/fixed_point.py',ROOT/'software/integer_weights.npz',ROOT/'data/fashion/t10k-images-idx3-ubyte',ROOT/'data/fashion/t10k-labels-idx1-ubyte',Path(__file__)]
    hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths if f.is_file()}
    results=[];started=perf_counter()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures={pool.submit(run_case,*case):case[0] for case in cases}
        for future in as_completed(futures):
            record=future.result();results.append(record);print(record['name'],'passed',f"{record['wall_seconds']:.2f}s",flush=True)
            (OUT/'verification_progress.json').write_text(json.dumps(results,indent=2))
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in hashes.items()),'Verified sources changed during regression'
    names=[c[0] for c in cases];results.sort(key=lambda r:names.index(r['name']))
    for case in results:
        if case['name'].startswith('lenet_'):
            assert len(case['frames'])==args.samples
            for frame in case['frames']:assert frame['traces']==8084 and frame['scores']==10 and frame['tiles']==6332
    result={'status':'passed','module_types':len(list((ROOT/'hardware/rtl').glob('*.v'))),'rtl_test_cohort':list(range(args.samples)),'official_test_images':10000,'official_test_scope':'Integer reference and PyTorch evaluated on 10000 images; RTL checks the explicit cohort only.','case_count':len(results),'cases':results,'wall_seconds':perf_counter()-started,'sha256':hashes,'vivado':{'status':'not_run','device_resources':None,'routed_timing':None,'total_on_chip_power_watts':None}}
    target=OUT/('verification_units.json' if args.units_only else ('verification_networks.json' if args.networks_only else 'verification.json'))
    target.write_text(json.dumps(result,indent=2))
    frames=[{'case':case['name'],**frame} for case in results for frame in case['frames']]
    if frames:
        with (OUT/'inference_measurements.csv').open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(frames[0]));wr.writeheader();wr.writerows(frames)
    print('PASS complete regression:',len(results),'cases',len(frames),'full-network executions',flush=True)
if __name__=='__main__':main()
