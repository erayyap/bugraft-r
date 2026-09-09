from pathlib import Path
import subprocess,json,sys,argparse
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from bugcraft_bench.pi_session import run

parser=argparse.ArgumentParser();parser.add_argument('--batch',action='store_true');parser.add_argument('--output');args=parser.parse_args()
batch=args.batch
a=root/(args.output or ('reports/batch-smoke' if batch else 'reports/pause-smoke'));a.mkdir(parents=True,exist_ok=True)
(a/'video.stop').unlink(missing_ok=True)
p=subprocess.Popen([str(root/'.venv/bin/python'),str(root/'scripts/record_desktop.py'),str(a/'video.mp4'),'--seconds','1220'])
try:
 prompt='This is a VM timing-control interface test, not a benchmark case. Do not type or interact with desktop applications. Use computer screenshot, then pause_vm, then screenshot while paused, then resume_vm, then screenshot. Confirm the reported VM states and finish. Do not open the Minecraft pause menu. The wall-clock budget is 20 minutes with no assistant-turn limit.'
 if batch:prompt+=' Execute the entire requested sequence in ONE computer batch call with an actions array. Verify the action log confirms every step and final VM running.'
 r=run(root,a,prompt)
 print(json.dumps(r),flush=True)
finally:
 (a/'video.stop').touch();p.wait(timeout=35)
