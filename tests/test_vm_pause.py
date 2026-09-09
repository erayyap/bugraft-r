import pytest
from computer_use import vm_pause

def test_transition_confirmed(monkeypatch):
    calls=[]
    def monitor(cmd):
        calls.append(cmd)
        return 'VM status: paused' if len(calls)>=3 else 'VM status: running'
    monkeypatch.setattr(vm_pause,'monitor',monitor)
    assert vm_pause.set_state('paused')=='paused'
    assert calls==['info status','stop','info status']

def test_bad_state_never_arbitrary_command():
    with pytest.raises(ValueError):vm_pause.monitor('quit')
    with pytest.raises(ValueError):vm_pause.set_state('shutdown')

def test_transition_requires_confirmation(monkeypatch):
    monkeypatch.setattr(vm_pause,'monitor',lambda cmd:'VM status: running')
    with pytest.raises(RuntimeError,match='not confirmed'):vm_pause.set_state('paused')

def test_already_running_no_cont(monkeypatch):
    calls=[]
    def monitor(cmd):calls.append(cmd);return 'VM status: running'
    monkeypatch.setattr(vm_pause,'monitor',monitor)
    assert vm_pause.set_state('running')=='running'
    assert calls==['info status','info status']
