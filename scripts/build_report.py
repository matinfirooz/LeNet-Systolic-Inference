from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from software.reporting import generate
if __name__=='__main__':
    generate(ROOT);print('Generated README, complete answers, evaluation, hardware guide and the exact 26-module port catalog.')
