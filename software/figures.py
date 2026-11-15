"""Source-aligned hardware diagrams and plots of measured data only."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from .schematic_symbols import Circuit,BLACK,CONTROL,GRAY,BLUE
from .data import load_idx,CLASSES

def system(root):
    c=Circuit('LeNet systolic inference architecture','32 x 32 padded input | 25 physical MAC PEs | WS / OS / IS specialization | signed 16-bit operands and 48-bit partial sums',w=20,h=12)
    control=c.block(.6,9.1,6.6,1.5,'Layer and tile controller','25 states | layer / N / M / K / post index',clocked=True,size=11)
    c.wire([(.6,11.2),(2.0,11.2),(2.0,10.6)],control=True,label='start / ready',at=(1.4,11.2))
    c.wire([control['R'],(8.3,9.85)],control=True,label='read / seed / run / commit',at=(7.75,9.85))
    px=c.block(.6,6.1,2.6,1.25,'Pixel frontend','u8 / 255; +2 zero border',clocked=True,size=9)
    c.wire([(.1,6.72),px['L']],8,at=(.34,6.72))
    c.text(1.9,7.85,'784 raw pixels\nvalid / ready',9,color=BLUE)
    ram=c.mem(4.6,5.3,3.2,2.8,'Activation SRAM',['bank 0: 8,192 words','bank 1: 8,192 words','source / destination swap'],16,8192)
    c.wire([px['R'],(3.8,6.725),(3.8,ram['A'][1]),ram['A']],16,at=(3.8,6.75))
    at=c.block(9.0,6.2,2.0,1.1,'A TILE','25 x 16, indexed write',clocked=True,size=9)
    c.wire([ram['Q'],(8.3,ram['Q'][1]),(8.3,at['L'][1]),at['L']],16,at=(8.3,6.55))
    dram=c.mem(.6,2.15,2.8,2.5,'Weight L2',['61,470 trained weights','four-cycle response'],16,61470)
    cache=c.mem(4.6,2.15,3.2,2.5,'Optional weight L1',['64 lines x 8 words','7-bit tag + valid per line','one-cycle hit response'],16,512)
    c.wire([dram['Q'],(4.05,dram['Q'][1]),(4.05,cache['A'][1]),cache['A']],16,'line refill',at=(4.05,3.6))
    bt=c.block(9.0,3.0,2.0,1.1,'B TILE','25 x 16, indexed write',clocked=True,size=9)
    c.wire([cache['Q'],(8.3,cache['Q'][1]),(8.3,bt['L'][1]),bt['L']],16,at=(8.3,3.55))
    grid=c.block(12.25,4.5,3.35,3.3,'',clocked=True)
    c.text(13.925,7.43,'5 x 5 MAC ARRAY',11,bold=True)
    c.text(13.925,4.96,'14 clocks per tile',9,color=GRAY)
    for r in range(5):
        for col in range(5):c.ax.add_patch(Rectangle((12.76+col*.46,5.4+r*.32),.32,.21,facecolor='#EDF3F6',edgecolor=BLACK,lw=.6,zorder=4))
    c.wire([at['R'],(11.5,6.75),(11.5,7.05),(12.25,7.05)],400,at=(11.5,6.88))
    c.wire([bt['R'],(11.6,3.55),(11.6,5.0),(12.25,5.0)],400,at=(11.6,4.1))
    acc=c.reg(16.8,5.4,2.1,1.5,'C TILE',1200,ce='seed | accumulate')
    c.wire([grid['R'],acc['D']],1200,at=(16.1,6.15))
    bias=c.mem(8.8,9.0,2.7,1.55,'Bias ROM',[],48,236)
    bias_reg=c.block(12.25,9.15,2.1,1.0,'BIAS TILE','5 x 48, indexed write',clocked=True,size=9)
    c.wire([bias['Q'],(11.85,bias['Q'][1]),(11.85,bias_reg['L'][1]),bias_reg['L']],48,at=(11.85,9.8))
    c.wire([bias_reg['R'],(16.4,9.65),(16.4,7.3),(17.3,7.3),(17.3,6.9)],240,'five seed biases',at=(16.4,8.4))
    select=c.block(16.8,3.95,2.1,.9,'25:1 SELECT','post_index',size=8.5)
    c.wire([acc['Q'],(19.4,6.15),(19.4,5.1),(16.3,5.1),(16.3,4.4),select['L']],1200,at=(17.6,5.1))
    nonlin=c.block(15.4,2.0,3.5,1.45,'Post-processing','tanh LUT | average-pool + tanh',clocked=True,size=10)
    c.wire([select['R'],(19.4,4.4),(19.4,3.65),(14.9,3.65),(14.9,2.725),nonlin['L']],48,at=(17.3,3.65))
    c.wire([nonlin['R'],(19.4,2.725),(19.4,1.25),(4.05,1.25),(4.05,5.7),(4.6,5.7)],16,'activation writeback',at=(10.5,1.25))
    sm=c.block(16.8,9.0,2.1,1.55,'Softmax / argmax','exp ROM + serial divide',clocked=True,size=8.8)
    logits=c.block(16.8,7.5,2.1,.8,'LOGITS','10 x 48, indexed write',clocked=True,size=8.5)
    c.wire([select['R'],(19.1,4.4),(19.1,7.2),(16.1,7.2),(16.1,7.9),logits['L']],48,at=(18.4,7.2));c.dot(19.1,4.4)
    c.wire([logits['R'],(19.4,7.9),(19.4,8.65),(16.3,8.65),(16.3,9.775),sm['L']],480,at=(18.6,8.65))
    c.wire([sm['R'],(19.8,9.775)],16,'scores',at=(19.4,9.775));c.wire([(18.9,9.3),(19.8,9.3)],4,'class',at=(19.4,9.3))
    c.text(6.2,.8,'Cache disabled: requests bypass L1 and use the same four-cycle L2.\nOne frame owns the memories until its final prediction is accepted.',9,color=GRAY)
    c.footer('hardware/rtl/lenet_core.v | authored hierarchical diagram; named control nets are shared')
    return c.save(root,'hardware/figures/architecture.png')

def array(root,mode):
    meaning={'ws':('Weight stationary','B[k,n]','A east / partial sum south','k','n'),
             'os':('Output stationary','C[m,n]','A east / B south','m','n'),
             'is':('Input stationary','A[m,k]','B south / partial sum east','m','k')}
    title,stationary,route,raxis,caxis=meaning[mode]
    c=Circuit(title+' : physical 5 x 5 array',f'PE row = {raxis}; PE column = {caxis} | local {stationary} | {route}',w=14,h=11)
    xs=[3.4+i*1.8 for i in range(5)];ys=[8.4-i*1.35 for i in range(5)];w=1.22;h=.8
    for r,y in enumerate(ys):
        for col,x in enumerate(xs):
            b=c.block(x,y-h/2,w,h,f'PE[{r},{col}]',f'hold {stationary[0]}[{r},{col}]',clocked=True,size=8)
            if col<4:c.wire([(x+w,y),(xs[col+1],y)],48 if mode=='is' else 16,at=(x+1.48,y))
            if r<4:c.wire([(x+w*.6,y-h/2),(x+w*.6,ys[r+1]+h/2)],48 if mode=='ws' else 16,at=(x+w*.6,y-.7))
        left='psum = 0' if mode=='is' else (f'A[m,{r}]' if mode=='ws' else f'A[{r},k]')
        c.wire([(1.65,y),(xs[0],y)],48 if mode=='is' else 16,left,at=(2.4,y))
        if mode!='is':c.text(.75,y,f'Delay {r}',8,color=CONTROL)
        c.wire([(xs[-1]+w,y),(13.1,y)],48 if mode=='is' else 16,at=(12.6,y))
        if mode=='is':c.text(13.1,y+.3,f'C[{r},n]',8)
    for col,x in enumerate(xs):
        label='psum = 0' if mode=='ws' else (f'B[k,{col}]' if mode=='os' else f'B[{col},n]')
        c.wire([(x+w*.6,9.3),(x+w*.6,ys[0]+h/2)],48 if mode=='ws' else 16,at=(x+w*.6,9.05))
        c.text(x+w*.6,9.55,label,8)
        if mode!='ws':c.text(x+w*.6,9.85,f'Delay {col}',7.5,color=CONTROL)
        c.wire([(x+w*.6,ys[-1]-h/2),(x+w*.6,2.2)],48 if mode=='ws' else 16,at=(x+w*.6,2.4))
        if mode=='ws':c.text(x+w*.6,1.95,f'C[m,{col}]',8)
    note={'ws':'B is loaded into 25 local registers before the wave. Bottom results are gathered by m and n.',
          'os':'All 25 accumulators hold C locally. Each PE receives five matching (A,B) pairs, then the tile is captured.',
          'is':'A is loaded into 25 local registers before the wave. Right-edge results are gathered by m and n.'}[mode]
    c.text(7,1.25,note,9,color=GRAY)
    c.text(7,.8,'All three cores compute the same signed C[5,5] = A[5,5] x B[5,5]. 13 wave clocks + 1 result-capture clock.',9,color=BLUE)
    c.footer(f'hardware/rtl/sa_{mode}_5x5.v | diagrams expand one physical tile, with skewed boundary streams')
    return c.save(root,f'hardware/figures/array_{mode}.png')

def pe(root,mode):
    c=Circuit('Processing element : '+mode.upper(),'16 x 16 signed product; sign extension to 48 bits; all state uses synchronous active-high reset',w=13,h=7)
    mul=c.alu(5.1,3.8,'x',.3);add=c.alu(7.9,3.8,'+',.3)
    if mode in ('ws','is'):
        local=c.reg(2.7,4.85,2.0,.9,'WEIGHT' if mode=='ws' else 'ACTIVATION',16,ce='load')
        c.wire([(.6,5.3),local['D']],16,'B[k,n]' if mode=='ws' else 'A[m,k]',at=(1.6,5.3))
        c.wire([local['Q'],(5.1,5.3),mul['T']],16,at=(5.1,4.85))
        c.wire([(.6,3.8),mul['L']],16,'A in' if mode=='ws' else 'B in',at=(2.1,3.8))
        forward=c.reg(3.0,1.4,1.6,.9,'FORWARD',16,ce='enable')
        c.wire([(2.1,3.8),(2.1,1.85),forward['D']],16,at=(2.1,2.8));c.dot(2.1,3.8)
        c.wire([forward['Q'],(5.65,1.85)],16,'A east' if mode=='ws' else 'B south',at=(5.15,1.85))
        c.wire([(7.9,5.9),add['T']],48,'psum in',at=(7.9,5.1))
        out=c.reg(9.4,3.2,2.0,1.2,'PSUM',48,ce='data_v & sum_v')
    else:
        c.wire([(.6,3.8),mul['L']],16,'A in (east)',at=(2.6,3.8))
        c.wire([(5.1,5.6),mul['T']],16,'B in (south)',at=(5.1,5.05))
        out=c.reg(9.4,3.2,2.0,1.2,'ACC',48,ce='A_v & B_v')
        c.wire([out['Q'],(12.0,3.8),(12.0,5.8),(7.9,5.8),add['T']],48,'feedback',at=(10.2,5.8))
        c.text(5.5,1.9,'Separate enabled A/B forwarding registers\ncarry each valid operand to its neighbor.',9,color=GRAY)
    c.wire([mul['R'],add['L']],32,'sign extend to 48',at=(6.45,3.8));c.wire([add['R'],out['D']],48,at=(8.9,3.8))
    c.wire([out['Q'],(12.4,3.8)],48,'C local' if mode=='os' else ('psum south' if mode=='ws' else 'psum east'),at=(12.0,3.8))
    c.text(6.5,.85,'Valid bits follow the same register boundaries as the arithmetic data; invalid waves do not accumulate.',8.6,color=GRAY)
    c.footer(f'hardware/rtl/pe_{mode}.v');return c.save(root,f'hardware/figures/pe_{mode}.png')

def memory(root):
    c=Circuit('Weight memory hierarchy','1 KiB data SRAM, plus 64 bytes of tag/valid metadata | 64 lines | eight 16-bit words per line',w=15,h=8)
    master=c.block(.6,3.7,2.5,1.5,'Tile loader','one outstanding word',clocked=True,size=10)
    ctrl=c.block(5.0,4.2,3.7,1.5,'Cache controller','IDLE / MISS_REQ / MISS_WAIT / RESP',clocked=True,size=9)
    l1=c.mem(5.0,1.2,3.7,2.2,'L1 SRAM',['hit: one clock','512 x 16 = 1,024 bytes'],16,512)
    l2=c.mem(11.0,3.6,3.2,2.5,'L2 DRAM model',['read latency: four clocks','all 61,470 weight words'],16,61470)
    c.wire([master['R'],(4.1,4.45),(4.1,4.95),ctrl['L']],16,'request address',at=(4.1,4.7))
    c.wire([ctrl['R'],(9.6,4.95),(9.6,l2['A'][1]),l2['A']],16,'line word address',at=(10.0,l2['A'][1]))
    c.wire([l2['Q'],(14.6,l2['Q'][1]),(14.6,.9),(4.5,.9),(4.5,l1['A'][1]),l1['A']],16,'eight-word refill; zero-pad final line',at=(11.3,.9))
    c.wire([l1['Q'],(9.4,l1['Q'][1]),(9.4,6.6),(3.7,6.6),(3.7,5.1),(3.1,5.1)],16,'held response / valid',at=(7.8,6.6))
    c.text(2.1,2.45,'Direct configuration:\nbypass L1 and use L2\nwith identical request semantics.',9,color=GRAY)
    c.text(11.9,2.5,'A miss finishes the complete line\nbefore marking its tag valid.\nBlocked responses remain stable.',9,color=GRAY)
    c.footer('hardware/rtl/weight_cache.v + dram_model.v | latency is measured between request and response handshakes')
    return c.save(root,'hardware/figures/memory_hierarchy.png')

def timing(root):
    f,ax=plt.subplots(figsize=(13,6));active=np.array([[int(r+c<=t<r+c+5) for t in range(14)] for r in range(5) for c in range(5)])
    ax.imshow(active,cmap='Blues',vmin=0,vmax=1,aspect='auto');ax.set(xticks=range(14),yticks=range(25),yticklabels=[f'PE({r},{c})' for r in range(5) for c in range(5)],xlabel='Wave clock after start (clock 13 captures the complete tile)',title='The three mappings share the same 14-clock tile schedule')
    ax.tick_params(axis='y',labelsize=7);ax.set_xticks(np.arange(-.5,14,1),minor=True);ax.set_yticks(np.arange(-.5,25,1),minor=True);ax.grid(which='minor',color='white',linewidth=.6)
    f.tight_layout();return pair(root,f,'hardware/figures/wavefront.png')

def pair(root,fig,relative):
    p=Path(root)/relative;p.parent.mkdir(parents=True,exist_ok=True);fig.savefig(p,dpi=170,bbox_inches='tight');fig.savefig(p.with_suffix('.svg'),bbox_inches='tight');plt.close(fig);return p

def software_plots(root):
    root=Path(root);raw,labels=load_idx(root/'data/fashion','t10k');paths=[]
    fig,axes=plt.subplots(2,10,figsize=(16,4))
    for j in range(10):
        image=raw[np.flatnonzero(labels==j)[0]];axes[0,j].imshow(image,cmap='gray',vmin=0,vmax=255);axes[0,j].set_title(CLASSES[j],fontsize=8)
        axes[1,j].imshow(np.pad(image,2),cmap='gray',vmin=0,vmax=255)
        for row in range(2):axes[row,j].axis('off')
    fig.suptitle('Fashion-MNIST: raw 28 x 28 images (top), exact two-pixel zero border to 32 x 32 (bottom)');fig.tight_layout();paths.append(pair(root,fig,'results/figures/data_padding.png'))
    history=json.loads((root/'results/software/training_history.json').read_text());epochs=[r['epoch'] for r in history]
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for key,label in [('train','Train'),('validation','Validation')]:
        axes[0].plot(epochs,[r[key+'_accuracy']*100 for r in history],label=label)
        axes[1].plot(epochs,[r[key+'_cross_entropy'] for r in history],label=label)
    axes[0].set(ylabel='Accuracy (%)',xlabel='Epoch',title='Measured training / validation accuracy');axes[1].set(ylabel='Cross-entropy',xlabel='Epoch',title='Validation selects the checkpoint')
    for ax in axes:ax.grid(alpha=.2);ax.legend()
    fig.tight_layout();paths.append(pair(root,fig,'results/figures/training.png'))
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,name,title in zip(axes,['float','integer'],['PyTorch float32','Integer Q12 reference']):
        out=np.load(root/f'results/software/{name}_test_outputs.npz');y=out['labels'];pred=out['predictions'];matrix=np.bincount(y.astype(int)*10+pred.astype(int),minlength=100).reshape(10,10)
        ax.imshow(matrix,cmap='Blues');ax.set(xticks=range(10),yticks=range(10),xlabel='Predicted class',ylabel='True class',title=title+f' : {100*np.mean(pred==y):.2f}%')
        for i in range(10):
            for j in range(10):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=6,color='white' if matrix[i,j]>500 else 'black')
    fig.suptitle('10,000 official test images; equal accuracy does not imply identical predictions');fig.tight_layout();paths.append(pair(root,fig,'results/figures/confusion.png'))
    q=json.loads((root/'results/software/quantization.json').read_text());fig,ax=plt.subplots(figsize=(9,3.4));ax.barh(['Different prediction','Same prediction'],[q['floating_integer_disagreements'],q['n_test']-q['floating_integer_disagreements']],color=[CONTROL,BLUE]);ax.set(xlabel='Official test images',title=f"Float / integer agreement: {100*q['prediction_agreement']:.2f}% ({q['floating_integer_disagreements']} different decisions)");ax.grid(axis='x',alpha=.2);fig.tight_layout();paths.append(pair(root,fig,'results/figures/agreement.png'))
    verification=root/'results/hardware/verification.json'
    if verification.exists():
        v=json.loads(verification.read_text());cases=[r for r in v['cases'] if r['name'].startswith('lenet_')];fig,axes=plt.subplots(1,2,figsize=(12,4))
        for cache,color in [(0,GRAY),(1,BLUE)]:
            group=[c for c in cases if c['parameters']['CACHE_ENABLE']==cache];x=np.arange(3)+(cache-.5)*.32
            axes[0].bar(x,[np.mean([f['compute_cycles'] for f in c['frames']]) for c in group],.32,label='L2 only' if cache==0 else '1 KiB L1',color=color)
            axes[1].bar(x,[np.mean([f['l2_reads'] for f in c['frames']]) for c in group],.32,label='L2 only' if cache==0 else '1 KiB L1',color=color)
        for ax in axes:ax.set_xticks(range(3),['WS','OS','IS']);ax.legend();ax.grid(axis='y',alpha=.2)
        axes[0].set(ylabel='Measured RTL clock cycles',title='Final pixel to prediction, ready consumers');axes[1].set(ylabel='Measured L2 word reads / image',title='Memory traffic on the same test cohort');fig.tight_layout();paths.append(pair(root,fig,'results/figures/cache_evaluation.png'))
    return paths

def generate(root):
    root=Path(root);paths=[system(root)]
    paths +=[array(root,m) for m in ['ws','os','is']]
    paths +=[pe(root,m) for m in ['ws','os','is']]
    paths +=[memory(root),timing(root)]
    paths +=software_plots(root)
    return paths
