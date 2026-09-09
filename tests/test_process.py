import os,signal,sys,time
from bugcraft_bench.process import stream_process

def test_sigterm_escalates(tmp_path):
    result=stream_process([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(30)'],cwd=tmp_path,env=os.environ,on_line=lambda *_:None,stop_reason=lambda:None,timeout=.4,term_grace=.2,drain_grace=.5)
    assert result['termination_reason']=='timeout'
    assert result['returncode']==-signal.SIGKILL
    assert result['elapsed_seconds']<2

def test_escaped_descendant_pipe_is_bounded(tmp_path):
    output=[]
    code='import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True);print(p.pid,flush=True)'
    try:
        result=stream_process([sys.executable,'-c',code],cwd=tmp_path,env=os.environ,on_line=lambda _,line:output.append(line),stop_reason=lambda:None,timeout=5,term_grace=.1,drain_grace=.4)
        assert result['elapsed_seconds']<2
    finally:
        for line in output:
            try:os.kill(int(line.strip()),signal.SIGKILL)
            except (ValueError,ProcessLookupError):pass
