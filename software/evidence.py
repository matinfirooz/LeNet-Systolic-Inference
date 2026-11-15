"""Accept saved results only while their source, ROM and dataset hashes match."""
import hashlib
import json
from pathlib import Path

def current(root,evidence):
    root=Path(root)
    if evidence.get('status')!='passed' or not evidence.get('sha256'):return False
    return all((root/name).is_file() and hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in evidence['sha256'].items())

def load(root):
    root=Path(root)
    names={'training':'results/software/training_summary.json','quantization':'results/software/quantization.json',
           'benchmark':'results/software/benchmark.json','rtl':'results/hardware/verification.json','generic':'results/hardware/generic_synthesis.json'}
    results={key:json.loads((root/name).read_text()) for key,name in names.items()}
    if not current(root,results['rtl']):raise ValueError('RTL evidence is absent or stale. Run scripts/run_verification.py.')
    if not current(root,results['generic']):raise ValueError('Generic synthesis evidence is absent or stale. Run scripts/run_generic_synthesis.py.')
    return results
