import json
from scripts.run_parallel_cases import refresh_usage
from scripts.index_sessions import index

def test_fleet_usage_counts_each_lane_once(tmp_path):
    for lane in (1,2):
        attempt=tmp_path/f'lane-{lane}/MC-{lane}-attempt';attempt.mkdir(parents=True)
        event={'type':'message_end','message':{'role':'assistant','usage':{'input':10,'output':2,'totalTokens':12,'cost':{'total':.02}}}}
        (attempt/'pi-transcript.jsonl').write_text(json.dumps(event)+'\n')
    refresh_usage(tmp_path)
    result=json.loads((tmp_path/'usage-summary.json').read_text())
    assert result['tokens']['totalTokens']==24
    assert result['pi_reported_cost_usd']['total']==.04
    assert len(result['attempts'])==2

def test_native_session_index_recurses_all_lanes(tmp_path):
    attempt=tmp_path/'lane-4/MC-1-attempt';sessions=attempt/'sessions';sessions.mkdir(parents=True)
    native=sessions/'session.jsonl';contents=json.dumps({'type':'session','id':'example'})+'\n';native.write_text(contents)
    (attempt/'manifest.json').write_text(json.dumps({'case_id':'MC-1','status':'completed'}))
    result=index(tmp_path)
    assert result['native_session_count']==1
    assert result['sessions'][0]['path']=='lane-4/MC-1-attempt/sessions/session.jsonl'
    assert native.read_text()==contents
