#!/usr/bin/env python3
"""Inventory complete native Pi session files; never replace them with summaries."""
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from bugcraft_bench.evidence import atomic_json,digest,utc

def index(run_dir):
 root=pathlib.Path(run_dir);entries=[]
 for session in sorted(root.glob('**/sessions/*.jsonl')):
  attempt=session.parent.parent
  manifest=json.loads((attempt/'manifest.json').read_text()) if (attempt/'manifest.json').exists() else {}
  session.parent.chmod(0o700);session.chmod(0o600)
  with session.open() as f:
   first=f.readline()
  try:header=json.loads(first)
  except json.JSONDecodeError:header={}
  entries.append({'attempt':str(attempt.relative_to(root)),'case_id':manifest.get('case_id'),'attempt_status':manifest.get('status'),'superseded':(attempt/'superseded.json').exists(),'session_id':header.get('id'),'path':str(session.relative_to(root)),'bytes':session.stat().st_size,'sha256':digest(session),'format':'native Pi session JSONL'})
 result={'updated_utc':utc(),'native_session_count':len(entries),'total_bytes':sum(e['bytes'] for e in entries),'sessions':entries,'preservation':'Original native session files retained, not shortened summaries. Includes superseded attempts. Private; review before export. Active-file hashes are point-in-time snapshots.'}
 atomic_json(root/'session-index.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run_dir',type=pathlib.Path);a=p.parse_args();r=index(a.run_dir);print(f"Indexed {r['native_session_count']} full native sessions ({r['total_bytes']} bytes)")
