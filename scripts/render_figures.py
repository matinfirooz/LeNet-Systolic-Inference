from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from software.figures import generate
if __name__=='__main__':print('Rendered',len(generate(ROOT)),'PNG/SVG figure pairs.')
