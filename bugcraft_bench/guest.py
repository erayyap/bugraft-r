import json,pathlib,time,uuid,urllib.request,re
from .evidence import atomic_json
from .lane import settings
class Guest:
    def __init__(self,root):self.root=root;self.control=settings(root).control
    def request(self,op,**kwargs):
        ident=uuid.uuid4().hex
        atomic_json(self.control/'request.json',dict(id=ident,op=op,**kwargs))
        end=time.monotonic()+60
        while time.monotonic()<end:
            try:
                j=json.loads((self.control/'response.json').read_text(encoding='utf-8-sig'))
                if j.get('request')==ident:
                    if not j['ok']:raise RuntimeError(j.get('error','Guest operation failed'))
                    return j
            except (FileNotFoundError,json.JSONDecodeError):pass
            time.sleep(.5)
        raise RuntimeError('Guest control timed out')
    def state(self):
        p=self.control/'state.json';last=None
        # The Windows controller writes state.tmp then renames it on an SMB
        # share.  During that replace window state.json can be absent or
        # incomplete for a few hundred milliseconds; do not turn that normal
        # heartbeat update into a false setup failure.
        for attempt in range(10):
            try:
                if time.time()-p.stat().st_mtime>15:raise RuntimeError('Guest heartbeat stale')
                return json.loads(p.read_text(encoding='utf-8-sig'))
            except (FileNotFoundError,json.JSONDecodeError) as exc:
                last=exc
                if attempt==9:break
                time.sleep(.2)
        raise RuntimeError('Guest heartbeat unavailable') from last
    def wait_window(self,timeout=600):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            s=self.state()
            if any(g['window'] for g in s['games']):time.sleep(8);return s
            time.sleep(2)
        raise RuntimeError('Minecraft window did not become ready')
def canonical(v):
    v=re.sub(r'^Minecraft\s+','',v)
    v=re.sub(r'\s+Pre-[Rr]elease\s+','-pre',v)
    return re.sub(r'\s+Release Candidate\s+','-rc',v)
def version_config(root,name):
    version=canonical(name);cache=root/'data/versions';cache.mkdir(exist_ok=True)
    path=cache/(version+'.json')
    if not path.exists():
        index=cache/'manifest.json'
        if not index.exists():
            with urllib.request.urlopen('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json',timeout=60) as r:index.write_bytes(r.read())
        meta=next((x for x in json.loads(index.read_text())['versions'] if x['id']==version),None)
        if meta is None:raise ValueError('Cannot map game version '+name)
        with urllib.request.urlopen(meta['url'],timeout=60) as r:path.write_bytes(r.read())
    j=json.loads(path.read_text());java=j.get('javaVersion',{}).get('majorVersion',8)
    return {'version':version,'java':8 if java<=8 else 17 if java<=17 else 21,'required_java':java,'release_time':j['releaseTime']}
