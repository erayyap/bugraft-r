import json
from bugcraft_bench.usage import summarize_events,collect

def event(kind='message_end',**changes):
    m={'id':'one','role':'assistant','stopReason':'toolUse','usage':{'input':10,'output':5,'cacheRead':20,'reasoning':3,'totalTokens':35,'cost':{'input':.01,'output':.02,'cacheRead':.003,'total':.033}}}
    m.update(changes);return json.dumps({'type':kind,'message':m})

def test_only_completed_messages_and_no_reasoning_double_count():
    r=summarize_events([event('message_update'),event(),event(),event(role='user')])
    assert r['tokens']['totalTokens']==35
    assert r['tokens']['reasoning']==3
    assert r['assistant_responses']==1
    assert r['pi_reported_cost_usd']['total']==.033

def test_missing_and_zero_pricing_not_assumed_free():
    r=summarize_events([event(usage={'input':10,'totalTokens':10,'cost':{'total':0}}),event(id='two',usage=None),'{partial'])
    assert r['tokens']['totalTokens']==10
    assert r['responses_missing_usage']==1
    assert any('not necessarily free' in w for w in r['warnings'])

def test_collect_idempotent(tmp_path):
    d=tmp_path/'MC-1-attempt';d.mkdir();(d/'pi-transcript.jsonl').write_text(event()+'\n')
    a=collect(tmp_path);b=collect(tmp_path)
    assert a['tokens']==b['tokens']
    assert b['pi_reported_cost_usd']['total']==.033
    assert (d/'usage.json').exists()
    assert (tmp_path/'usage-summary.json').exists()
