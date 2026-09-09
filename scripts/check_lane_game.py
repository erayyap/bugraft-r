#!/usr/bin/env python3
"""One lane's setup-only Minecraft readiness gate; not an evaluated attempt."""
import argparse,os,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from bugcraft_bench.guest import Guest
from bugcraft_bench.lane import settings
from bugcraft_bench.evidence import atomic_json,utc
from vncdotool import api
p=argparse.ArgumentParser();p.add_argument('--lane',required=True,choices=['1','2','3','4']);a=p.parse_args();os.environ['BUGCRAFT_LANE']=a.lane
lane=settings(root);out=root/f'reports/four-lane-setup/lane-{a.lane}';out.mkdir(parents=True,exist_ok=True)
g=Guest(root)
try:
 g.request('stop');g.request('launch',attempt=f'lane-{a.lane}-readiness',version='24w44a',java=21)
 state=g.wait_window(timeout=180);g.request('focus')
 with api.connect(lane.vnc,timeout=15) as c:c.captureScreen(str(out/'minecraft.png'))
 atomic_json(out/'readiness.json',{'lane':lane.id,'container':lane.container,'game_window_present':True,'manual_main_menu_review_pending':True,'utc':utc(),'state':state,'setup_only':True})
 print('Game window ready:',lane.container,flush=True)
except Exception as exc:
 atomic_json(out/'readiness.json',{'lane':lane.id,'game_window_present':False,'error':str(exc),'utc':utc(),'setup_only':True})
 raise
