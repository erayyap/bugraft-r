"""Sequential resumable Windows baseline. Provisioning/evaluation stay outside Pi."""
import argparse,json,pathlib,shutil,subprocess,time,uuid,threading,os
from vncdotool import api
from .guest import Guest,version_config
from .pi_session import run as pi_run,MODEL
from computer_use.vm_pause import PROTOCOL,set_state
from .evidence import atomic_json,utc,digest,disk_guard,redact
from .crash_detection import classify,provider_signals_from_events,provider_block_signals
from .hang_detection import probe as probe_hang, VERSION as HANG_VERSION
from .lane import settings
from .usage import collect as collect_usage
from scripts.index_sessions import index as index_sessions

def collect(root,g,attempt,ident):
    g.request('collect');source=g.control.parent/'evidence'/ident
    for p in source.rglob('*'):
        if not p.is_file():continue
        dest=attempt/'game'/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix in ('.txt','.log','.json','.cfg'):dest.write_text(redact(p.read_text(errors='replace')))
        elif p.suffix=='.gz':
            import gzip
            try:dest.with_suffix('').write_text(redact(gzip.decompress(p.read_bytes()).decode(errors='replace')))
            except Exception:raise RuntimeError('Cannot sanitize compressed game log')
    return source

def attempt_case(root,run_dir,case):
    disk_guard(root,25)
    ident=case['id']+'-'+uuid.uuid4().hex[:8];attempt=run_dir/ident;attempt.mkdir()
    start=time.monotonic();g=Guest(root);video=None;capture_watch_stop=threading.Event()
    meta={'lane':settings(root).id,'vm_container':settings(root).container,'hang_detection_version':HANG_VERSION,'timing_protocol':PROTOCOL,'case_id':case['id'],'attempt_id':ident,'started_utc':utc(),'model':MODEL,'thinking':'medium','input_sha256':digest(root/'data/inputs'/(case['id']+'.json')),'environment_sha256':digest(root/'reports/setup/environment.json'),'official':True,'status':'preparing','harness_sha256':{str(p.relative_to(root)):digest(p) for p in [*sorted((root/'bugcraft_bench').glob('*.py')),root/'scripts/record_desktop.py',root/'vm/shared/guest-control.ps1',root/'computer_use/vm_pause.py',root/'vm/shared/Capture.cs']}}
    atomic_json(attempt/'manifest.json',meta)
    result=None
    try:
        cfg=version_config(root,case['versions'][0]);meta['version_config']=cfg
        # New instance and fresh world directory every attempt; shared immutable downloads only.
        set_state('running');g.request('stop');g.request('launch',attempt=ident,version=cfg['version'],java=cfg['java'])
        state=g.wait_window();g.request('focus');time.sleep(5)
        with api.connect(settings(root).vnc,timeout=15) as client:client.captureScreen(str(attempt/'start.png'))
        meta['status']='evaluating';meta['agent_started_utc']=utc();atomic_json(attempt/'manifest.json',meta)
        video=subprocess.Popen([str(root/'.venv/bin/python'),str(root/'scripts/record_desktop.py'),str(attempt/'video.mp4'),'--seconds','1320'],stdout=subprocess.DEVNULL,stderr=(attempt/'capture-stderr.txt').open('w'))
        def watch_capture():
            while not capture_watch_stop.wait(1):
                if video.poll() is not None:
                    if not (attempt/'video.json').exists() or video.returncode!=0:(attempt/'evidence-abort').touch()
                    return
        threading.Thread(target=watch_capture,daemon=True).start()
        prompt=(f'Reproduce the reported Minecraft Java crash or freeze through the Windows game UI. The game version is {cfg["version"]}, currently freshly launched; create any needed new singleplayer world through the UI. You may use in-game commands through chat. Do not use shell/game-file modifications or external resources to reproduce the issue. Use the computer tool for gameplay. Stop when the reported crash or freeze occurs, or when you cannot make progress. For a suspected freeze, resume the VM first and check responsiveness through screenshots and ordinary game inputs; intentional VM pause is not a freeze. Describe only observed evidence. End with one line OBSERVED_OUTCOME: crash, freeze, or not_reproduced. Time limit: 20 minutes. There is no assistant-turn limit.\n\n'
                f'Bug report {case["id"]}\nTitle: {case["title"]}\nDescription:\n{case["description"]}\nReporter environment:\n{case["environment"]}\nComments available before triage:\n'+ '\n\n'.join(case['comments']))
        pr=pi_run(root,attempt,prompt)
        meta['status']='post_evaluation_probe';atomic_json(attempt/'manifest.json',meta)
        hang=probe_hang(g,attempt)
        (attempt/'video.stop').touch();video.wait(timeout=35)
        capture=json.loads((attempt/'video.json').read_text())
        state=g.state();collect(root,g,attempt,ident)
        reports=list((attempt/'game/crash-reports').glob('*.txt'))
        report='\n'.join(p.read_text(errors='replace') for p in reports)
        log=(attempt/'game/logs/latest.log');logs=log.read_text(errors='replace') if log.exists() else ''
        with (attempt/'pi-transcript.jsonl').open(errors='replace') as events:provider_history=provider_signals_from_events(events)
        provider_signals=provider_block_signals(pr.get('terminal_error') or '')
        result=classify(report=report,logs=logs,process_exited=not state['game_running'],timed_out=pr['termination_reason'] in ('timeout','turn_limit'),provider_blocked=bool(provider_signals),hang_evidence=hang)
        if provider_history:result['provider_flag_history']=provider_history
        if provider_signals:result['provider_blocked_signals']=provider_signals
        elif (pr['returncode']!=0 or pr['agent_error']) and pr['termination_reason']=='agent_completed':result={'outcome':'agent_error','reason':'Pi process or final model response failed'}
        if not provider_signals and not pr['tool_inventory_valid']:result={'outcome':'invalid_harness','reason':'Actual tool/model/skill inventory did not match'}
        if capture['capture_error'] or pr['termination_reason'] in ('disk_watermark','evidence_limit','capture_error'):result={'outcome':'evidence_error','reason':capture['capture_error'] or pr['termination_reason']}
        result.update({'hang_evidence':hang,'hang_detection_version':HANG_VERSION,'pi':pr,'crash_report_files':[str(p.relative_to(attempt)) for p in reports],'requires_manual_crash_adjudication':bool(reports)})
    except Exception as exc:
        result={'outcome':'setup_blocked' if meta['status']=='preparing' else 'harness_error','reason':type(exc).__name__+': '+str(exc)}
    finally:
        capture_watch_stop.set()
        if video and video.poll() is None:
            (attempt/'video.stop').touch()
            try:video.wait(timeout=35)
            except subprocess.TimeoutExpired:video.terminate();result={'outcome':'evidence_error','reason':'Recorder did not terminate cleanly'}
        try:
            set_state('running');collect(root,g,attempt,ident);g.request('stop');g.request('remove_worlds')
        except Exception as exc:
            if result is not None:result['cleanup_error']=str(exc)
        meta.update(status='completed',ended_utc=utc(),elapsed_seconds=time.monotonic()-start)
        atomic_json(attempt/'manifest.json',meta);atomic_json(attempt/'result.json',result)
        collect_usage(run_dir);index_sessions(run_dir)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',default='reports/full-run');p.add_argument('--case',action='append',help='Issue ID; repeat to run a selected subset');p.add_argument('--resume',action='store_true');p.add_argument('--lane',choices=['1','2','3','4']);a=p.parse_args()
    if a.lane:os.environ['BUGCRAFT_LANE']=a.lane
    root=pathlib.Path(__file__).resolve().parents[1];run_dir=root/a.run_dir;run_dir.mkdir(parents=True,exist_ok=True)
    gate=json.loads((root/'reports/final-smoke/gate.json').read_text());assert gate['passed']
    for name,key in [('computer_use/extension.ts','extension'),('computer_use/helper.py','helper'),('computer_use/SKILL.md','skill'),('computer_use/vm_pause.py','vm_control')]:
        if digest(root/name)!=gate['inventory'][key]:raise RuntimeError('Harness changed since smoke; rerun interface smoke')
    env=json.loads((root/'reports/setup/environment.json').read_text());assert env['vm_ready']
    cases=[json.loads(p.read_text()) for p in sorted((root/'data/inputs').glob('MC-*.json'))]
    if a.case:
        by_id={c['id']:c for c in cases}
        missing=set(a.case)-set(by_id)
        if missing:raise ValueError('Unknown case IDs: '+', '.join(sorted(missing)))
        cases=[by_id[key] for key in dict.fromkeys(a.case)]
    completed={}
    if a.resume:
        for d in run_dir.iterdir():
            if (d/'result.json').exists() and not (d/'superseded.json').exists():
                m=json.loads((d/'manifest.json').read_text());r=json.loads((d/'result.json').read_text())
                if m.get('timing_protocol')==PROTOCOL and r['outcome'] not in ('setup_blocked','harness_error','invalid_harness','evidence_error') and m['input_sha256']==digest(root/'data/inputs'/(m['case_id']+'.json')) and m['environment_sha256']==digest(root/'reports/setup/environment.json'):
                    completed[m['case_id']]=r
    for c in cases:
        if c['id'] in completed:continue
        r=attempt_case(root,run_dir,c);completed[c['id']]=r
        counts={}
        for result in completed.values():counts[result['outcome']]=counts.get(result['outcome'],0)+1
        atomic_json(run_dir/'summary.json',{'updated_utc':utc(),'dataset_count':len(cases),'recorded_count':len(completed),'counts':counts,'cases':{k:v['outcome'] for k,v in completed.items()},'not_run':[c['id'] for c in cases if c['id'] not in completed],'model':MODEL,'thinking':'medium'})
        print(utc(),c['id'],r['outcome'],r.get('reason',''),flush=True)
        if r['outcome'] in ('harness_error','invalid_harness','evidence_error'):raise RuntimeError('Fix harness before continuing')
if __name__=='__main__':main()
