import pytest
from computer_use import helper

class Screen:size=(100,100)
class Client:
 screen=Screen()
 def refreshScreen(self):pass

def test_batch_validates_all_before_any_action(monkeypatch):
 called=[]
 monkeypatch.setattr(helper,'perform',lambda *a,**k:called.append(1))
 with pytest.raises(ValueError):helper.execute(Client(),{'action':'batch','actions':[{'action':'pause_vm'},{'action':'click','x':500,'y':0}]})
 assert not called

def test_batch_stops_on_failure(monkeypatch):
 seen=[]
 monkeypatch.setattr(helper.vm_pause,'state',lambda:'running')
 monkeypatch.setattr(helper,'screenshot',lambda c:{'image':'test'})
 def perform(c,a,**kw):
  seen.append(a['action'])
  if a['action']=='key':raise RuntimeError('input fault')
 monkeypatch.setattr(helper,'perform',perform)
 r=helper.execute(Client(),{'action':'batch','actions':[{'action':'screenshot'},{'action':'key','keys':['w']},{'action':'pause_vm'}]})
 assert seen==['screenshot','key']
 assert [x['status'] for x in r['action_log']]==['completed','failed']
 assert 'input fault' in r['error']

@pytest.mark.parametrize('steps',[[],[{'action':'screenshot'}]*17,[{'action':'batch','actions':[]}],[{'action':'wait','duration':5}]*6])
def test_batch_bounds(steps):
 with pytest.raises(ValueError):helper.batch_steps({'action':'batch','actions':steps},100,100)

def test_batch_resume_then_pause(monkeypatch):
 state=['paused'];seen=[]
 monkeypatch.setattr(helper.vm_pause,'state',lambda:state[0])
 monkeypatch.setattr(helper,'screenshot',lambda c:{'image':'test'})
 def perform(c,a,**kw):
  seen.append(a['action'])
  if a['action']=='resume_vm':state[0]='running'
  if a['action']=='pause_vm':state[0]='paused'
 monkeypatch.setattr(helper,'perform',perform)
 r=helper.execute(Client(),{'action':'batch','actions':[{'action':'resume_vm'},{'action':'key','keys':['w']},{'action':'pause_vm'}]})
 assert 'error' not in r and r['vm_state']=='paused'
 assert seen==['resume_vm','key','pause_vm']
