"""Package the complete trained, verified project, with paths preserved."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    excluded={'__pycache__','.ipynb_checkpoints','.venv','.Xil'}
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and not any(part in excluded for part in p.parts)
           and p.suffix not in {'.pyc','.vvp','.jou'} and not str(p.relative_to(ROOT)).startswith('results/hardware/build/')
           and p.name!='FILE_MANIFEST.json']
    manifest=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    (ROOT/'FILE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    target=ROOT.parent/'HW3_Matin_Firoozbakht.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in files+[ROOT/'FILE_MANIFEST.json']:z.write(p,p.relative_to(ROOT.parent))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for name in ['README.md','COMPLETE_ANSWERS.md','HW3_Matin_Firoozbakht.ipynb','software/lenet_fashion_mnist.pt','hardware/rtl/lenet_core.v','results/hardware/verification.json','data/fashion/train-images-idx3-ubyte.gz']:
            assert 'HW3_Matin_Firoozbakht/'+name in z.namelist()
    print('Complete project:',target.name,'|',len(files)+1,'files |',target.stat().st_size,'bytes')
if __name__=='__main__':main()
