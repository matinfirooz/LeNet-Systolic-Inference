"""Official Fashion-MNIST IDX files, verified downloads and disjoint splits."""
import gzip
import hashlib
import json
import struct
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

FILES={
 'train-images-idx3-ubyte.gz':'8d4fb7e6c68d591d4c3dfef9ec88bf0d',
 'train-labels-idx1-ubyte.gz':'25c81989df183df01b3e8a0aad5dffbe',
 't10k-images-idx3-ubyte.gz':'bef4ecab320f06d8554ea6380940ec79',
 't10k-labels-idx1-ubyte.gz':'bb300cfdad3c16e7a12a480ee83cd310',
}
BASE='https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion/'
CLASSES=['T-shirt/top','Trouser','Pullover','Dress','Coat','Sandal','Shirt','Sneaker','Bag','Ankle boot']

def download(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    def one(item):
        name,expected=item;p=root/name
        if not p.exists():
            with urllib.request.urlopen(BASE+name,timeout=90) as response:p.write_bytes(response.read())
        data=p.read_bytes()
        if hashlib.md5(data).hexdigest()!=expected:raise ValueError('Checksum mismatch: '+name)
        if name.startswith('t10k'): (root/name.removesuffix('.gz')).write_bytes(gzip.decompress(data))
        return {'file':name,'source':BASE+name,'bytes':len(data),'md5':expected,'sha256':hashlib.sha256(data).hexdigest()}
    with ThreadPoolExecutor(max_workers=4) as pool:manifest=list(pool.map(one,FILES.items()))
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

def load_idx(root,kind='train'):
    root=Path(root)
    image=gzip.decompress((root/(kind+'-images-idx3-ubyte.gz')).read_bytes())
    label=gzip.decompress((root/(kind+'-labels-idx1-ubyte.gz')).read_bytes())
    magic,n,h,w=struct.unpack('>4I',image[:16]);lm,ln=struct.unpack('>2I',label[:8])
    if (magic,lm,h,w)!=(2051,2049,28,28) or n!=ln:raise ValueError('Invalid IDX header')
    x=np.frombuffer(image,dtype=np.uint8,offset=16).reshape(n,28,28).copy()
    y=np.frombuffer(label,dtype=np.uint8,offset=8).copy()
    if len(image)!=16+n*784 or len(label)!=8+n or y.max()>9:raise ValueError('Invalid IDX payload')
    return x,y

def split_indices(labels,seed=42):
    rng=np.random.default_rng(seed);train=[];valid=[]
    for c in range(10):
        indexes=np.flatnonzero(labels==c);rng.shuffle(indexes)
        valid.extend(indexes[:600]);train.extend(indexes[600:])
    return np.sort(np.array(train,dtype=np.int64)),np.sort(np.array(valid,dtype=np.int64))
