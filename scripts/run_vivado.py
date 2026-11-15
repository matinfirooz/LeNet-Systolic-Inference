"""Build all six physically specialized implementations with identical constraints."""
import json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    executable=shutil.which('vivado')
    if not executable:raise SystemExit('Vivado is not installed/on PATH. Install locally; routed timing, mapped resources and power cannot be measured here.')
    for mode in ['ws','os','is']:
        for cache in [0,1]:
            env=os.environ.copy();env.update(LENET_DATAFLOW=mode,LENET_CACHE=str(cache))
            subprocess.run([executable,'-mode','batch','-source','hardware/scripts/build_vivado.tcl'],cwd=ROOT,env=env,check=True)
if __name__=='__main__':main()
