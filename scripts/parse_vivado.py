"""Read actual routed reports. Missing measurements remain null."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read_config(mode,cache):
    p=ROOT/f'results/vivado/{mode}_cache{cache}';meta=p/'implementation.json'
    result={'dataflow':mode.upper(),'cache_enable':cache,'status':'not_run','clock_period_ns':None,'setup_wns_ns':None,'hold_whs_ns':None,'total_on_chip_power_watts':None,'activity':None,'LUTs':None,'FFs':None,'DSPs':None,'BRAM_tiles':None}
    if meta.exists():
        text=meta.read_text().strip();text=text if text.startswith('{') else '{'+text+'}'
        result.update(json.loads(text));result['status']='reports_present_requires_qualification'
    power=p/'power_route.rpt'
    if power.exists():
        m=re.search(r'Total On-Chip Power\s*\(W\)\s*\|\s*([0-9.]+)',power.read_text())
        if m:result['total_on_chip_power_watts']=float(m.group(1))
    usage=p/'utilization_route.rpt'
    if usage.exists():
        text=usage.read_text()
        for field,patterns in {'LUTs':['Slice LUTs','CLB LUTs'],'FFs':['Slice Registers','CLB Registers'],'DSPs':['DSPs','DSP48E1'],'BRAM_tiles':['Block RAM Tile']}.items():
            for label in patterns:
                match=re.search(r'\|\s*'+re.escape(label)+r'\s*\*?\s*\|\s*([0-9.,]+)',text)
                if match:result[field]=float(match.group(1).replace(',',''));break
    return result
def main():
    rows=[read_config(m,c) for m in ['ws','os','is'] for c in [0,1]]
    p=ROOT/'results/hardware/vivado_summary.json';p.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
