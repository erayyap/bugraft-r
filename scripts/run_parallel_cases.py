#!/usr/bin/env python3
"""Fixed-size VM-lane scheduler. Fresh run, one job per VM, no case retries."""
import argparse,collections,json,os,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from bugcraft_bench.evidence import atomic_json,utc,disk_guard,digest
from bugcraft_bench.usage import summarize_events,TOKEN_FIELDS,COST_FIELDS
from scripts.index_sessions import index as index_sessions


def refresh_usage(out):
    attempts={}
    for path in out.glob('lane-*/*/pi-transcript.jsonl'):
        with path.open(errors='replace') as f:attempts[str(path.parent.relative_to(out))]=summarize_events(f)
    atomic_json(out/'usage-summary.json',{'updated_utc':utc(),'tokens':{k:sum(v['tokens'][k] for v in attempts.values()) for k in TOKEN_FIELDS},'pi_reported_cost_usd':{k:sum(v['pi_reported_cost_usd'][k] for v in attempts.values()) for k in COST_FIELDS},'cost_basis':'Pi-reported estimate, not billed cost','attempts':attempts})


def main():
    p=argparse.ArgumentParser();p.add_argument('--selection',type=pathlib.Path,required=True);p.add_argument('--run-dir',type=pathlib.Path,required=True);p.add_argument('--concurrency',type=int,choices=range(1,5),default=4);a=p.parse_args()
    out=(root/a.run_dir).resolve()
    if out.exists():raise RuntimeError('Fresh trial requires a new run directory')
    ids=json.loads(a.selection.read_text())['case_ids']
    if not ids or len(ids)!=len(set(ids)):raise ValueError('Case selection must be nonempty and unique')
    for case in ids:
        if not (root/'data/inputs'/f'{case}.json').exists():raise ValueError('Unknown case '+case)
    disk_guard(root,30);out.mkdir(parents=True);(out/'orchestration').mkdir()
    pending=collections.deque(ids);active={};finished={};blocked=False;last_usage=0
    atomic_json(out/'run-manifest.json',{'started_utc':utc(),'case_ids':ids,'concurrency':a.concurrency,'model':'openai-codex/gpt-6-astra','thinking':'medium','agent_timeout_seconds':1200,'assistant_turn_limit':None,'native_sessions_preserved':True,'new_world_per_attempt':True,'one_live_flag_nudge_max':1,'lane_configuration_sha256':digest(root/'vm/lanes/config.json')})
    while pending or active:
        disk_guard(root)
        if not blocked:
            for lane in range(1,a.concurrency+1):
                if not pending:break
                if lane in active:continue
                case=pending.popleft();lane_dir=out/f'lane-{lane}';lane_dir.mkdir(exist_ok=True)
                logpath=out/'orchestration'/f'{case}-lane-{lane}.log'
                cmd=[str(root/'.venv/bin/python'),'-u','-m','bugcraft_bench.runner','--run-dir',str(lane_dir),'--lane',str(lane),'--case',case]
                with logpath.open('w') as log:proc=subprocess.Popen(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                active[lane]={'case_id':case,'proc':proc,'pid':proc.pid,'started_utc':utc()}
                print(utc(),'START',case,'lane',lane,'pid',proc.pid,flush=True)
        for lane,job in list(active.items()):
            code=job['proc'].poll()
            if code is None:continue
            candidates=[]
            for directory in (out/f'lane-{lane}').iterdir():
                if directory.is_dir() and (directory/'result.json').exists():
                    m=json.loads((directory/'manifest.json').read_text())
                    if m['case_id']==job['case_id']:candidates.append(directory)
            if len(candidates)==1:
                d=candidates[0];result=json.loads((d/'result.json').read_text());record={'lane':lane,'attempt':str(d.relative_to(out)),'outcome':result['outcome'],'process_returncode':code}
            else:record={'lane':lane,'outcome':'runner_error','process_returncode':code,'reason':'Expected exactly one completed attempt artifact'}
            finished[job['case_id']]=record;del active[lane]
            if record['outcome'] in ('runner_error','harness_error','invalid_harness','evidence_error'):blocked=True
            print(utc(),'FINISH',job['case_id'],record['outcome'],flush=True)
        status={'updated_utc':utc(),'requested_cases':ids,'concurrency':a.concurrency,'active':{str(l):{k:v for k,v in j.items() if k!='proc'} for l,j in active.items()},'pending':list(pending),'finished':finished,'completed_count':len(finished),'blocked':blocked,'state':'completed' if len(finished)==len(ids) else 'blocked' if blocked and not active else 'running'}
        atomic_json(out/'progress.json',status)
        if time.monotonic()-last_usage>=15:
            refresh_usage(out);last_usage=time.monotonic()
        if blocked and not active:break
        if pending or active:time.sleep(2)
    refresh_usage(out);index_sessions(out)
    atomic_json(out/'summary.json',status)
    print(utc(),'TRIAL',status['state'],'completed',len(finished),'of',len(ids),flush=True)
if __name__=='__main__':main()
