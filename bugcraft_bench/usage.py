"""Summarize Pi message_end usage exactly once, not streaming deltas.

Costs are Pi-reported estimates, not provider invoices. Reasoning tokens are a
reported subcategory and are not added again to totalTokens/output.
"""
import json
from pathlib import Path
from .evidence import atomic_json,utc,digest

TOKEN_FIELDS=('input','output','cacheRead','cacheWrite','reasoning','totalTokens')
COST_FIELDS=('input','output','cacheRead','cacheWrite','total')

def summarize_events(lines):
    tokens={k:0 for k in TOKEN_FIELDS};cost={k:0.0 for k in COST_FIELDS}
    responses=errors=missing_usage=missing_cost=0;seen=set()
    for line in lines:
        try:event=json.loads(line)
        except (json.JSONDecodeError,UnicodeDecodeError):continue
        if event.get('type')!='message_end':continue
        message=event.get('message',{})
        if message.get('role')!='assistant':continue
        ident=message.get('id')
        if ident:
            if ident in seen:continue
            seen.add(ident)
        responses+=1;errors+=int(message.get('stopReason')=='error')
        usage=message.get('usage')
        if not isinstance(usage,dict):missing_usage+=1;continue
        for key in TOKEN_FIELDS:tokens[key]+=usage.get(key,0) or 0
        quoted=usage.get('cost')
        if not isinstance(quoted,dict) or 'total' not in quoted:
            missing_cost+=1;continue
        for key in COST_FIELDS:cost[key]+=quoted.get(key,0) or 0
    warnings=[]
    if tokens['totalTokens']>0 and cost['total']==0:warnings.append('Pi reports zero cost despite token usage; pricing may be unavailable, not necessarily free.')
    if missing_usage:warnings.append('Some assistant responses lack usage data.')
    if missing_cost:warnings.append('Some usage records lack cost data; cost total is partial.')
    return {'tokens':tokens,'pi_reported_cost_usd':cost,'assistant_responses':responses,'error_responses':errors,'responses_missing_usage':missing_usage,'responses_missing_cost':missing_cost,'cost_basis':'Pi-reported estimate, not billed cost','reasoning_token_note':'Reported separately; not added again to output or totalTokens','warnings':warnings}

def collect(run_dir):
    run_dir=Path(run_dir);by_attempt={}
    for attempt in sorted(run_dir.iterdir()):
        transcript=attempt/'pi-transcript.jsonl'
        if not attempt.is_dir() or not transcript.exists():continue
        with transcript.open(errors='replace') as f:usage=summarize_events(f)
        usage.update(updated_utc=utc(),source='pi-transcript.jsonl: assistant message_end usage',collector_sha256=digest(Path(__file__)))
        atomic_json(attempt/'usage.json',usage)
        by_attempt[attempt.name]=usage
    tokens={k:sum(v['tokens'][k] for v in by_attempt.values()) for k in TOKEN_FIELDS}
    cost={k:sum(v['pi_reported_cost_usd'][k] for v in by_attempt.values()) for k in COST_FIELDS}
    summary={'updated_utc':utc(),'tokens':tokens,'pi_reported_cost_usd':cost,'cost_basis':'Pi-reported estimate, not billed cost','scope':'All recorded attempts in this run directory, including retries/errors; not smoke/setup-worker usage','attempt_count':len(by_attempt),'attempts':by_attempt}
    atomic_json(run_dir/'usage-summary.json',summary)
    return summary
