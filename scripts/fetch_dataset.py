#!/usr/bin/env python3
"""Fetch pinned public report JSON only; never download prior trajectories."""
import concurrent.futures, hashlib, json, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
def get(url):
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read()
def main():
    meta = json.loads(get('https://huggingface.co/api/models/erayyapagci/bugcraft-dataset'))
    revision = meta['sha']
    files = sorted(x['rfilename'] for x in meta['siblings'] if x['rfilename'].endswith('/issue.json'))
    destination = ROOT / 'data' / 'source'
    def fetch(name):
        data = get(f'https://huggingface.co/erayyapagci/bugcraft-dataset/resolve/{revision}/{name}')
        json.loads(data)
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, files))
    (destination/'manifest.json').write_text(json.dumps({'repo_type':'model','revision':revision,'files':records}, indent=2))
    print(f'Fetched {len(records)} reports at {revision}')
if __name__ == '__main__': main()
