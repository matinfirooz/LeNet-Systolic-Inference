from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from software.data import download
if __name__=='__main__':
    for item in download(ROOT/'data/fashion'):print(item['file'],item['bytes'],'verified')
