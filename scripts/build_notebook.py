"""Build a complete, reviewable notebook from the implemented sources and measured answers."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    cells=[]
    def md(s):cells.append({'cell_type':'markdown','id':f'hw3-{len(cells):03d}','metadata':{},'source':(s.strip()+'\n').splitlines(True)})
    def code(s):cells.append({'cell_type':'code','id':f'hw3-{len(cells):03d}','metadata':{},'source':(s.strip()+'\n').splitlines(True),'execution_count':None,'outputs':[]})
    report=(ROOT/'COMPLETE_ANSWERS.md').read_text();parts=report.split('\n## ');sections={p.split('\n',1)[0]:p for p in parts[1:]}
    md('# LeNet: Complete Software and Systolic Hardware Answers\n\n**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)\n\nThe full checkpoint, dataset, RTL and actual results are included in the companion ZIP. Open this notebook from its extracted project directory. All computations and diagrams describe the implemented design. Saved evidence is checked against source and data hashes.\n\nDefault execution loads the trained checkpoint. Set `RETRAIN=True` and `RUN_RTL=True` to retrain and requalify the design. Vivado physical metrics are unmeasured; supplied scripts run that flow locally.')
    code('''import json
import sys
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from IPython.display import display, Image, Code, Markdown
ROOT=Path.cwd()
if not (ROOT/'software/model.py').exists():
    raise FileNotFoundError('Extract HW3_Matin_Firoozbakht.zip and open this notebook from that project directory.')
sys.path.insert(0,str(ROOT))
RETRAIN=False
RUN_RTL=False
print('Matin Firoozbakht | @matinfirooz')''')
    for key in ['1. Specification and implementation scope','2. Dataset, preprocessing and training']:
        md('## '+sections[key])
    code('''if RETRAIN:
    subprocess.run([sys.executable,'scripts/train.py','--epochs','20','--threads','4'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/export_evaluate.py','--rtl-images','16'],cwd=ROOT,check=True)
history=json.loads((ROOT/'results/software/training_history.json').read_text())
training=json.loads((ROOT/'results/software/training_summary.json').read_text())
display(pd.DataFrame(history))
display(pd.DataFrame([training['test']]))
for name in ['data_padding.png','training.png']:
    display(Image(filename=str(ROOT/'results/figures'/name)))''')
    md('### Complete PyTorch implementation\n\nThe source follows the layer table, including tanh after average pooling. Cross-entropy receives raw logits; inference emits softmax scores.')
    code('''for name in ['software/data.py','software/model.py','scripts/train.py']:
    display(Markdown('#### '+name))
    display(Code((ROOT/name).read_text(),language='python'))''')
    code('''import torch
torch.set_num_threads(1)
from software.model import LeNet, prepare_pixels
from software.data import load_idx
from software.fixed_point import infer_integer
model=LeNet()
model.load_state_dict(torch.load(ROOT/'software/lenet_fashion_mnist.pt',map_location='cpu',weights_only=True)['state_dict'])
model.eval()
raw,labels=load_idx(ROOT/'data/fashion','t10k')
q=dict(np.load(ROOT/'software/integer_weights.npz'))
with torch.inference_mode():
    probabilities=model.probabilities(prepare_pixels(raw[:4])).numpy()
integer=infer_integer(raw[:4],q,trace=True)
display(pd.DataFrame({'label':labels[:4],'float_class':probabilities.argmax(1),'integer_class':integer['predictions']}))
print('Trainable parameters:',sum(p.numel() for p in model.parameters()))
print('Intermediate values per image:',integer['trace'].shape[1])''')
    for key in ['3. Convolution as a folded matrix product','4. Three physical dataflows']:
        md('## '+sections[key])
    code('''for mode in ['ws','os','is']:
    display(Image(filename=str(ROOT/f'hardware/figures/array_{mode}.png')))
    display(Image(filename=str(ROOT/f'hardware/figures/pe_{mode}.png')))''')
    md('### Complete HDL source\n\nAll 26 source modules are shown below. The top-level controller computes every layer autonomously; the host supplies raw image pixels only.')
    code('''for path in sorted((ROOT/'hardware/rtl').glob('*.v')):
    display(Markdown('#### '+path.name))
    display(Code(path.read_text(),language='verilog'))''')
    md('## '+sections['5. Numeric formats and nonlinear operations'])
    code('''quantization=json.loads((ROOT/'results/software/quantization.json').read_text())
display(pd.DataFrame(quantization['accumulator_bounds']))
display(pd.DataFrame([{'tensor':k,'clips':v} for k,v in quantization['weight_bias_clips'].items()]))
for name in ['software/fixed_point.py','scripts/export_evaluate.py']:
    display(Code((ROOT/name).read_text(),language='python'))
for name in ['confusion.png','agreement.png']:
    display(Image(filename=str(ROOT/'results/figures'/name)))''')
    md('## '+sections['6. Memory hierarchy, ownership and interfaces'])
    code('''for name in ['architecture.png','memory_hierarchy.png','wavefront.png']:
    display(Image(filename=str(ROOT/'hardware/figures'/name)))''')
    md('## '+sections['7. Actual RTL verification'])
    code('''if RUN_RTL:
    subprocess.run([sys.executable,'scripts/run_verification.py','--samples','16','--jobs','3'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/run_generic_synthesis.py'],cwd=ROOT,check=True)
from software.evidence import load
evidence=load(ROOT)
print('Source/ROM/dataset hashes match actual RTL and generic synthesis evidence.')
display(pd.DataFrame([{'case':case['name'],'status':case['status'],'full_inferences':len(case['frames'])} for case in evidence['rtl']['cases']]))
for case in evidence['rtl']['cases']:
    for message in case['pass_messages']:print(message)
display(pd.DataFrame([{'top':case['top'],'cache':case['cache_enable'],'PE_multipliers':len(case['compute_pe_multipliers']),'generic_memories':case['generic_memories'],'inferred_latches':case['inferred_latches']} for case in evidence['generic']['cases']]))''')
    for key in ['8. Evaluation 1: speed and fairness','9. Evaluation 2: throughput and power','10. Bonus: measured two-level-memory effect']:
        md('## '+sections[key])
    code('''evaluation=json.loads((ROOT/'results/evaluation.json').read_text())
display(pd.DataFrame(evaluation['hardware']))
display(Image(filename=str(ROOT/'results/figures/cache_evaluation.png')))
benchmark=json.loads((ROOT/'results/software/benchmark.json').read_text())
display(pd.DataFrame([{key:value for key,value in result.items() if key!='samples_ms'} for result in benchmark['results'].values()],index=list(benchmark['results'])))
print('Hardware timing columns are target-clock projections, not routed device measurements.')''')
    md('## '+sections['11. Reproduction and evidence limits'])
    code('''subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True,capture_output=True,text=True)
assert len(list((ROOT/'hardware/rtl').glob('*.v')))==26
assert len(raw)==10000 and len(labels)==10000
assert evaluation['rtl_evidence_current'] and evaluation['generic_evidence_current']
print('All eight Python arithmetic/data tests pass. All 26 modules and complete answers are present.')
display(Markdown((ROOT/'README.md').read_text()))''')
    md('## '+sections['Sources'])
    notebook={'cells':cells,'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12','file_extension':'.py','mimetype':'text/x-python'},'authors':[{'name':'Matin Firoozbakht','github':'https://github.com/matinfirooz'}]}}
    target=ROOT/'HW3_Matin_Firoozbakht.ipynb';target.write_text(json.dumps(notebook,indent=1,ensure_ascii=False));print('Built',len(cells),'notebook cells.')
if __name__=='__main__':main()
