"""Bit-exact Q12 activations/weights and Q24 48-bit accumulators."""
from pathlib import Path
import numpy as np

LAYERS=[('conv1',1,32,6,28,25,0,0),('conv3',6,14,16,10,150,150,6),
        ('conv5',16,5,120,1,400,2550,22),('fc6',120,1,84,1,120,50550,142),('fc7',84,1,10,1,84,60630,226)]
TRACE_OFFSETS=[0,4704,5880,7480,7880,8000]
TRACE_WORDS=8084

def quantize(weights):
    result={};clips={}
    for name,value in weights.items():
        scale=1<<24 if name.endswith('bias') else 1<<12
        v=np.floor(value.astype(np.float64)*scale+.5).astype(np.int64)
        low,high=(-(1<<47),(1<<47)-1) if name.endswith('bias') else (-32768,32767)
        clips[name]=int(np.count_nonzero((v<low)|(v>high)))
        result[name]=np.clip(v,low,high)
    result['tanh_lut']=np.floor(np.tanh(np.arange(-2048,2049,dtype=np.float64)/256)*4096+.5).astype(np.int64)
    result['exp_lut']=np.floor(np.exp(-np.arange(4097,dtype=np.float64)/256)*(1<<24)+.5).astype(np.int64)
    return result,clips

def tanh_acc(acc,lut):
    address=np.clip((acc+32768)>>16,-2048,2048)+2048
    return lut[address]

def conv_integer(x,w,b,lut):
    bs,cin,iw,_=x.shape;cout=w.shape[0];ow=iw-4
    patches=np.lib.stride_tricks.sliding_window_view(x,(5,5),axis=(2,3))
    a=np.ascontiguousarray(patches.transpose(0,2,3,1,4,5).reshape(-1,cin*25))
    acc=a@w.reshape(cout,-1).T+b
    return tanh_acc(acc,lut).reshape(bs,ow,ow,cout).transpose(0,3,1,2).copy()

def pool_integer(x,lut):
    total=x[:,:,0::2,0::2]+x[:,:,0::2,1::2]+x[:,:,1::2,0::2]+x[:,:,1::2,1::2]
    return tanh_acc(total<<10,lut)

def infer_integer(raw,q,trace=False):
    x=np.pad((raw.astype(np.int64)*4096+127)//255,((0,0),(2,2),(2,2)))[:,None,:,:]
    values=[];lut=q['tanh_lut']
    x=conv_integer(x,q['conv1.weight'],q['conv1.bias'],lut);values.append(x)
    x=pool_integer(x,lut);values.append(x)
    x=conv_integer(x,q['conv3.weight'],q['conv3.bias'],lut);values.append(x)
    x=pool_integer(x,lut);values.append(x)
    x=conv_integer(x,q['conv5.weight'],q['conv5.bias'],lut).reshape(len(raw),120);values.append(x)
    x=tanh_acc(x@q['fc6.weight'].T+q['fc6.bias'],lut);values.append(x)
    logits=x@q['fc7.weight'].T+q['fc7.bias']
    address=np.clip((logits.max(1,keepdims=True)-logits+32768)>>16,0,4096)
    exps=q['exp_lut'][address];probabilities=np.minimum(65535,(exps<<16)//exps.sum(1,keepdims=True))
    result={'logits':logits,'probabilities':probabilities,'predictions':logits.argmax(1)}
    if trace:result['trace']=np.concatenate([v.reshape(len(raw),-1) for v in values],axis=1)
    return result

def write_hex(path,values,width):
    mask=(1<<width)-1
    Path(path).write_text(''.join(f'{int(v)&mask:0{width//4}x}\n' for v in np.asarray(values).reshape(-1)))
