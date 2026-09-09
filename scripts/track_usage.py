#!/usr/bin/env python3
import argparse,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bugcraft_bench.usage import collect
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True,type=Path);p.add_argument('--pid-file',type=Path);a=p.parse_args()
while True:
    collect(a.run_dir)
    if not a.pid_file:break
    try:
        pid=int(a.pid_file.read_text());os.kill(pid,0)
        if Path('/proc',str(pid),'stat').read_text().split(') ')[1].startswith('Z'):break
    except (FileNotFoundError,ProcessLookupError):break
    time.sleep(15)
