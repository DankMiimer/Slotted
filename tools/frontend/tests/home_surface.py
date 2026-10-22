"""Validate actual home-console renders against the production layout (MIT).

Run under run_probe.sh: python3 home_surface.py PROBE [SLOT].
"""
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.frontend.home_assets import HOMES
probe=Path(sys.argv[1]).resolve()
slot=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'theme/art-book-slot/_slot'
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);rows=[]
    for model in HOMES:
        run=subprocess.run([str(probe),str(slot),str(tmp/'frame.bmp'),model,'front'],text=True,capture_output=True)
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        fields={line.split()[0]:line.split()[2:] for line in run.stdout.splitlines() if line.startswith(('bounds ','contact '))}
        rows.append(' '.join([model]+fields['bounds']+fields['contact']))
    subprocess.run(['g++','-std=c++11',str(ROOT/'tools/frontend/tests/home_layout.cpp'),'-o',str(tmp/'layout')],check=True)
    subprocess.run([str(tmp/'layout')],input='\n'.join(rows),text=True,check=True)
