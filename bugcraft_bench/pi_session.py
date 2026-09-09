import json,os,pathlib,shutil,time
from .evidence import atomic_json,redact,utc,disk_guard
from .process import stream_process
from computer_use.vm_pause import set_state,PROTOCOL
from .lane import settings
from .continuation import eligible,NUDGE,POLICY
MODEL='openai-codex/gpt-6-astra'
FLAGS=['--no-extensions','--no-skills','--no-prompt-templates','--no-context-files','--no-themes','--no-approve']
def command(root,attempt):
    return ['pi','--model',MODEL,'--thinking','medium',*FLAGS,'--extension',str(root/'computer_use/extension.ts'),'--skill',str(root/'computer_use/SKILL.md'),'--tools','read,bash,edit,write,computer','--mode','json','--session-dir',str(attempt/'sessions'),'--print']
def run(root,attempt,prompt,timeout=1200):
    attempt=attempt.resolve();attempt.mkdir(parents=True,exist_ok=True)
    for d in ('work','screenshots','sessions'):(attempt/d).mkdir(exist_ok=True)
    private=root/'.runtime'/attempt.name;private.mkdir(parents=True,exist_ok=True);private.chmod(0o700)
    auth=pathlib.Path.home()/'.pi/agent/auth.json'
    shutil.copyfile(auth,private/'auth.json');(private/'auth.json').chmod(0o600)
    (private/'settings.json').write_text('{}')
    env={k:os.environ[k] for k in ('PATH','HOME','LANG','NODE_EXTRA_CA_CERTS','SSL_CERT_FILE') if k in os.environ}
    env.update({'PI_CODING_AGENT_DIR':str(private),'PI_OFFLINE':'1','BUGCRAFT_HARNESS_ROOT':str(root),'BUGCRAFT_INVENTORY':str(attempt/'inventory.json'),'BUGCRAFT_SCREENSHOT_DIR':str(attempt/'screenshots'),'BUGCRAFT_VM_TIMING':str(attempt/'vm-timing.jsonl')})
    if 'BUGCRAFT_LANE' in os.environ:env['BUGCRAFT_LANE']=os.environ['BUGCRAFT_LANE']
    session_file=attempt/'sessions/session.jsonl'
    base_command=command(root,attempt)+['--session',str(session_file)]
    cmd=base_command+['--','/skill:computer-use '+prompt]
    (attempt/'prompt.txt').write_text(prompt)
    turns=0;size=0;agent_error=False;error_responses=0;terminal_error=None
    started=time.monotonic();deadline=started+timeout;continuation_nudges=0;segments=[]
    try:
        set_state('running')
        with (attempt/'pi-transcript.jsonl').open('w') as transcript,(attempt/'pi-stderr.txt').open('w') as errors:
            def on_line(name,line):
                nonlocal size,turns,agent_error,error_responses,terminal_error
                safe=redact(line);size+=len(safe.encode())
                f=transcript if name=='stdout' else errors;f.write(safe);f.flush()
                if name=='stdout':
                    try:
                        j=json.loads(line)
                        if j.get('type')=='turn_end':turns+=1
                        if j.get('type')=='message_end' and j.get('message',{}).get('role')=='assistant':
                            message=j['message'];agent_error=message.get('stopReason')=='error'
                            terminal_error=redact(message.get('errorMessage','')) if agent_error else None
                            error_responses+=int(agent_error)
                    except json.JSONDecodeError:pass
            def stop_reason():
                try:disk_guard(root)
                except RuntimeError:return 'disk_watermark'
                if size>300*1024**2:return 'evidence_limit'
                video=attempt/'video.json'
                if video.exists():
                    try:
                        if json.loads(video.read_text()).get('capture_error'):return 'capture_error'
                    except json.JSONDecodeError:pass
                if (attempt/'evidence-abort').exists():return 'capture_error'
                return None
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    status={'returncode':None,'termination_reason':'timeout','elapsed_seconds':time.monotonic()-started}
                    break
                status=stream_process(cmd,cwd=attempt/'work',env=env,on_line=on_line,stop_reason=stop_reason,timeout=remaining)
                segments.append(dict(status))
                remaining=deadline-time.monotonic()
                if not eligible(terminal_error=terminal_error,used=continuation_nudges,remaining=remaining,session_exists=session_file.exists(),stop_reason=status['termination_reason']):break
                if stop_reason():break
                continuation_nudges+=1
                event={'utc':utc(),'policy':POLICY,'nudge_number':continuation_nudges,'message':NUDGE,'remaining_seconds':remaining,'same_session':str(session_file.relative_to(attempt)),'same_world':True,'model':MODEL,'thinking':'medium'}
                with (attempt/'continuation-events.jsonl').open('a') as log:log.write(json.dumps(event)+'\n')
                cmd=base_command+['--',NUDGE]
                # No cleanup, world restart, provider change or context removal.
                # The next process opens the exact same native session file.
                agent_error=False;terminal_error=None
            status['elapsed_seconds']=time.monotonic()-started
        inventory=json.loads((attempt/'inventory.json').read_text()) if (attempt/'inventory.json').exists() else {}
        validated=(inventory.get('lane')==settings(root).id and set(inventory.get('tools',[]))=={'read','bash','edit','write','computer'} and inventory.get('model')=='gpt-6-astra' and inventory.get('provider')=='openai-codex' and inventory.get('thinking')=='medium' and inventory.get('skills')==['skill:computer-use'])
        result={'continuation_policy':POLICY,'continuation_nudges':continuation_nudges,'segments':segments,'native_session':str(session_file.relative_to(attempt)),'lane':settings(root).id,'vm_container':settings(root).container,'timing_protocol':PROTOCOL,'model':MODEL,'thinking':'medium','clean_flags':FLAGS,'tool_inventory_valid':validated,**status,'agent_error':agent_error,'terminal_error':terminal_error,'error_responses':error_responses,'turns':turns,'ended_utc':utc(),'inventory':inventory,'isolation':'default Pi builtins plus computer; no OS sandbox; evaluator data omitted from prompt/work but host-access remains a residual limitation'}
        atomic_json(attempt/'pi-result.json',result);return result
    finally:
        try:set_state('running')
        finally:shutil.rmtree(private,ignore_errors=True)
