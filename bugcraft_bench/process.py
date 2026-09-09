"""Bounded subprocess groups and pipe draining, including orphaned pipe holders."""
import os,selectors,signal,subprocess,time

def stream_process(command,*,cwd,env,on_line,stop_reason,timeout,term_grace=3,drain_grace=6):
    p=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    selector=selectors.DefaultSelector();buffers={};started=time.monotonic();stopping=None;reason='agent_completed';killed=False
    for name in ('stdout','stderr'):
        stream=getattr(p,name);os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name);buffers[name]=b''
    def send(sig):
        try:os.killpg(p.pid,sig)
        except ProcessLookupError:pass
    try:
        while selector.get_map():
            now=time.monotonic()
            requested=stop_reason()
            if now-started>=timeout:requested='timeout'
            # A leader exit does not guarantee descendant-held pipe EOF.
            if p.poll() is not None and stopping is None:
                stopping=now
            if requested and reason=='agent_completed':reason=requested;stopping=now;send(signal.SIGTERM)
            if stopping is not None:
                if now-stopping>=term_grace and not killed:send(signal.SIGKILL);killed=True
                if now-stopping>=drain_grace:break
            for key,_ in selector.select(.1):
                try:data=os.read(key.fileobj.fileno(),65536)
                except BlockingIOError:continue
                name=key.data
                if not data:selector.unregister(key.fileobj);continue
                buffers[name]+=data
                if len(buffers[name])>24*1024**2:
                    reason='evidence_limit'
                    if stopping is None:stopping=now;send(signal.SIGTERM)
                while b'\n' in buffers[name]:
                    line,buffers[name]=buffers[name].split(b'\n',1);on_line(name,line.decode('utf-8',errors='replace')+'\n')
        for name,data in buffers.items():
            if data:on_line(name,data.decode('utf-8',errors='replace'))
    finally:
        selector.close()
        if p.poll() is None:send(signal.SIGKILL)
        for name in ('stdout','stderr'):getattr(p,name).close()
    try:code=p.wait(timeout=2)
    except subprocess.TimeoutExpired:code=None;reason='process_reap_timeout'
    return {'returncode':code,'termination_reason':reason,'elapsed_seconds':time.monotonic()-started,'sigkill_sent':killed}
