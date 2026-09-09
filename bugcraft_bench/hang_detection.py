"""Evaluator-only application responsiveness evidence, not a target-bug oracle."""
import json,time
from pathlib import Path
from vncdotool import api
from computer_use.vm_pause import state,set_state
from .evidence import atomic_json,utc
from .lane import settings

VERSION='window-probe-v1'

def assess(samples,agent_reported_freeze=False):
    # Never regard pausing virtual CPUs, a replaced process or an arbitrary
    # Win32 error as proof that Minecraft itself stopped responding.
    candidates=[]
    for sample in samples:
        if sample.get('vm_before')!='running' or sample.get('vm_after')!='running':continue
        rows={}
        for w in sample.get('windows',[]):
            timed_out=(not w.get('responded') and w.get('win32_error') in (0,1460) and w.get('elapsed_ms',0)>=1400)
            if timed_out:rows[(w['pid'],w['handle'])]=w
        candidates.append(set(rows))
    common=set.intersection(*candidates) if len(candidates)>=3 and len(candidates)==len(samples) else set()
    if common:
        return {'status':'window_hang_observed','target_confirmed':False,'reason':'Same Minecraft window failed three 1500ms message probes while VM and guest controller remained responsive; target identity requires review','windows':[{'pid':p,'handle':h} for p,h in sorted(common)]}
    if agent_reported_freeze:
        return {'status':'reported_freeze_unconfirmed','target_confirmed':False,'reason':'Agent reported a freeze but repeated window-hang evidence is absent; responsive UI does not rule out simulation freeze'}
    return {'status':'no_window_hang_detected','target_confirmed':False,'reason':'No confirmed window-message hang; this does not rule out a simulation-only freeze'}

def reported_freeze(transcript):
    """Only an explicit final claim, never arbitrary report/tool text."""
    import re
    last=''
    if not Path(transcript).exists():return False
    for line in Path(transcript).open(errors='replace'):
        try:event=json.loads(line)
        except json.JSONDecodeError:continue
        m=event.get('message',{})
        if event.get('type')=='message_end' and m.get('role')=='assistant' and m.get('stopReason')=='stop':
            last='\n'.join(c.get('text','') for c in m.get('content',[]) if c.get('type')=='text')
    return bool(re.search(r'(?im)^\s*OBSERVED_OUTCOME:\s*(?:freeze|hang)\s*$',last))

def probe(guest,attempt):
    attempt=Path(attempt);out=attempt/'freeze-probe';out.mkdir(parents=True,exist_ok=True)
    samples=[];started=utc();error=None
    try:
        # Only after model evaluation has ended; no inputs fed back to agent.
        set_state('running')
        for i in range(3):
            before=state();sample=guest.request('probe_window');after=state()
            sample.update(vm_before=before,vm_after=after,host_utc=utc())
            samples.append(sample)
            with api.connect(settings().vnc,timeout=10) as client:client.captureScreen(str(out/f'{i}.png'))
            atomic_json(out/'samples.json',samples)
            if not sample.get('windows'):break
            if i<2:time.sleep(2)
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    claim=reported_freeze(attempt/'pi-transcript.jsonl')
    result=assess(samples,claim)
    if error:result.update(status='probe_error',reason=error,target_confirmed=False)
    result.update(version=VERSION,started_utc=started,ended_utc=utc(),samples=samples,agent_reported_freeze=claim,phase='post-evaluation diagnostics; not extra agent time')
    atomic_json(out/'result.json',result)
    return result
