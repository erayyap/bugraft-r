import json
import pytest
from bugcraft_bench.continuation import eligible,NUDGE
from bugcraft_bench import pi_session

FLAG='Codex error: This content was flagged for possible cybersecurity risk.'

def test_one_nudge_only_with_live_session_and_budget():
    base=dict(terminal_error=FLAG,used=0,remaining=100,session_exists=True,stop_reason='agent_completed')
    assert eligible(**base)
    for change in ({'used':1},{'remaining':0},{'session_exists':False},{'stop_reason':'timeout'},{'terminal_error':'fetch failed'}):
        assert not eligible(**(base|change))
    assert NUDGE=='continue.'

@pytest.mark.parametrize('second_error',[False,True])
def test_same_session_one_nudge_original_deadline(monkeypatch,tmp_path,second_error):
    home=tmp_path/'home';auth=home/'.pi/agent/auth.json';auth.parent.mkdir(parents=True);auth.write_text('{}')
    monkeypatch.setattr(pi_session.pathlib.Path,'home',classmethod(lambda cls:home))
    monkeypatch.delenv('BUGCRAFT_LANE',raising=False)
    root=tmp_path/'root';root.mkdir();attempt=root/'reports/case';calls=[];timeouts=[];vm=[];clock=[100.0]
    monkeypatch.setattr(pi_session.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(pi_session,'disk_guard',lambda *a:None)
    monkeypatch.setattr(pi_session,'set_state',lambda x:vm.append(x))
    def fake_stream(command,*,on_line,timeout,**kwargs):
        calls.append(command);timeouts.append(timeout);clock[0]+=10
        session=pi_session.pathlib.Path(command[command.index('--session')+1]);session.write_text('preserved session')
        inventory={'lane':0,'tools':['read','bash','edit','write','computer'],'provider':'openai-codex','model':'gpt-6-astra','thinking':'medium','skills':['skill:computer-use']}
        (attempt/'inventory.json').write_text(json.dumps(inventory))
        failure=len(calls)==1 or second_error
        message={'role':'assistant','stopReason':'error' if failure else 'stop','errorMessage':FLAG if failure else None}
        on_line('stdout',json.dumps({'type':'message_end','message':message})+'\n')
        return {'returncode':0,'termination_reason':'agent_completed','elapsed_seconds':10}
    monkeypatch.setattr(pi_session,'stream_process',fake_stream)
    result=pi_session.run(root,attempt,'Minecraft test',timeout=1200)
    assert len(calls)==2 and calls[1][-1]=='continue.'
    assert calls[0][calls[0].index('--session')+1]==calls[1][calls[1].index('--session')+1]
    assert timeouts==[1200,1190]
    assert result['elapsed_seconds']==20 and result['continuation_nudges']==1
    assert result['agent_error']==second_error
    assert vm==['running','running']  # No cleanup/restart between the two calls.
    assert len((attempt/'continuation-events.jsonl').read_text().splitlines())==1
    assert not (root/'.runtime/case').exists()
