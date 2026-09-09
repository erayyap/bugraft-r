import json
from bugcraft_bench.hang_detection import assess,reported_freeze
from bugcraft_bench.crash_detection import classify

def sample(pid=1,responded=False,error=1460,vm='running',elapsed=1500):
 return {'vm_before':vm,'vm_after':vm,'windows':[{'pid':pid,'handle':99,'responded':responded,'win32_error':error,'elapsed_ms':elapsed}]}

def test_three_timeouts_observe_hang_not_target_success():
 h=assess([sample() for _ in range(3)])
 assert h['status']=='window_hang_observed' and h['target_confirmed'] is False
 assert classify(hang_evidence=h)['outcome']=='hang_observed_unconfirmed_target'

def test_paused_vm_never_hang():
 assert assess([sample(vm='paused') for _ in range(3)])['status']=='no_window_hang_detected'

def test_responsive_sample_or_pid_change_never_confirmed():
 assert assess([sample(),sample(responded=True),sample()])['status']!='window_hang_observed'
 assert assess([sample(1),sample(2),sample(3)])['status']!='window_hang_observed'

def test_arbitrary_api_errors_not_hangs():
 assert assess([sample(error=5) for _ in range(3)])['status']!='window_hang_observed'
 assert assess([sample(elapsed=5) for _ in range(3)])['status']!='window_hang_observed'

def test_claim_not_proof():
 h=assess([sample(responded=True) for _ in range(3)],True)
 assert h['status']=='reported_freeze_unconfirmed' and not h['target_confirmed']
 assert classify(hang_evidence=h)['outcome']=='freeze_reported_unconfirmed'

def test_claim_only_from_final_assistant(tmp_path):
 p=tmp_path/'events.jsonl'
 def e(role,text,stop='stop'):return json.dumps({'type':'message_end','message':{'role':role,'stopReason':stop,'content':[{'type':'text','text':text}]}})+'\n'
 p.write_text(e('user','OBSERVED_OUTCOME: freeze')+e('assistant','OBSERVED_OUTCOME: not_reproduced'))
 assert not reported_freeze(p)
 p.write_text(e('assistant','OBSERVED_OUTCOME: freeze'))
 assert reported_freeze(p)

def test_crash_evidence_preserved_over_hang():
 h=assess([sample() for _ in range(3)])
 assert classify(report='---- Minecraft Crash Report ----',hang_evidence=h)['outcome']=='unrelated_or_unconfirmed_crash'
