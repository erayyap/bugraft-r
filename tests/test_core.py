import importlib.util,pathlib,sys
import pytest
from bugcraft_bench.dataset import normalize
from bugcraft_bench.crash_detection import classify,provider_block_signals
from bugcraft_bench.evidence import redact,atomic_json

def test_crash_not_exit():
    assert classify(process_exited=True)['outcome']=='process_exit'
    assert classify(report='MC-1 java.lang.NullPointerException')['outcome']=='no_crash'
def test_crash_requires_specific_evidence():
    report='---- Minecraft Crash Report ----\njava.lang.NullPointerException\nat sample.Renderer.draw'
    assert classify(report=report)['outcome']=='unrelated_or_unconfirmed_crash'
    assert classify(report=report,version_matches=True,signature={'exception':'java.lang.NullPointerException','context':['sample.Renderer.draw']})['outcome']=='crash_match'
    assert classify(report=report,version_matches=False,signature={'exception':'java.lang.NullPointerException','context':['sample.Renderer.draw']})['outcome']!='crash_match'
def test_crash_preserved_at_timeout():
    assert classify(report='---- Minecraft Crash Report ----',timed_out=True)['outcome']=='unrelated_or_unconfirmed_crash'
def test_provider_block_is_separate_and_not_retried():
    text='Provider error: request was blocked by the content policy.'
    assert provider_block_signals(text)==['content_policy','request_blocked','blocked_by_policy']
    result=classify(report='---- Minecraft Crash Report ----',provider_blocked=True)
    assert result['outcome']=='provider_blocked'
    assert 'retry' in result['reason']
def test_redaction():
    assert 'secretvalue' not in redact('access_token=secretvalue refreshToken: secretvalue Authorization: Bearer secretvalue')
    assert 'devicelogin' not in redact('https://microsoft.com/devicelogin?code=abc')
def test_rollback_and_comments():
    issue={'key':'MC-1','fields':{'summary':'solution','description':'corrected','versions':[{'name':'1.2'}], 'comment':{'comments':[{'created':'2024-01-01T01:00:00Z','body':'original'},{'created':'2024-01-03T00:00:00Z','body':'leak'}]}},'changelog':{'total':1,'histories':[{'created':'2024-01-02T00:00:00Z','author':{'displayName':'[Helper] Someone'},'items':[{'field':'summary','fromString':'raw','toString':'solution'},{'field':'description','fromString':'initial','toString':'corrected'}]}]}}
    result=normalize(issue)
    assert result['title']=='raw' and result['description']=='initial'
    assert result['comments']==['original']
def test_incomplete_history_rejected():
    with pytest.raises(ValueError):normalize({'key':'MC-1','fields':{},'changelog':{'total':2,'histories':[]}})

def helper():
    spec=importlib.util.spec_from_file_location('helper',pathlib.Path(__file__).parents[1]/'computer_use/helper.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
@pytest.mark.parametrize('action',[{'action':'click','x':100,'y':0},{'action':'wait','duration':6},{'action':'type','text':'a'*2001},{'action':'click','x':-1,'y':4}])
def test_input_bounds(action):
    with pytest.raises(ValueError):helper().validate(action,100,100)
def test_release_on_error(monkeypatch):
    h=helper();released=[]
    class Screen:size=(100,100)
    class Client:
        screen=Screen()
        def refreshScreen(self):pass
        def keyDown(self,k):pass
        def keyUp(self,k):released.append(k)
    monkeypatch.setattr(h.time,'sleep',lambda _:(_ for _ in ()).throw(RuntimeError('fault')))
    with pytest.raises(RuntimeError):h.perform(Client(),{'action':'key','keys':['ctrl','a']})
    assert released==['a','ctrl']

def test_provider_risk_flag_only_from_error_event():
    import json
    from bugcraft_bench.crash_detection import provider_signals_from_events
    text='Codex error: This content was flagged for possible cybersecurity risk.'
    error={'type':'message_end','message':{'role':'assistant','stopReason':'error','errorMessage':text}}
    assert 'cybersecurity_risk_flag' in provider_signals_from_events([json.dumps(error)])
    user={'type':'message_end','message':{'role':'user','content':text}}
    assert not provider_signals_from_events([json.dumps(user)])
