"""Reconstruct only pre-triage report content from public Jira history."""
import copy, datetime, hashlib, json, pathlib, re
TRUSTED=re.compile(r'\[(?:Helper|Mod|Mojang)\]', re.I)
def stamp(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
def normalize(issue):
    f=copy.deepcopy(issue['fields']); histories=issue['changelog']['histories']
    if issue['changelog']['total']!=len(histories):raise ValueError('Incomplete history: '+issue['key'])
    histories=sorted(histories,key=lambda h:stamp(h['created']))
    trusted=[h for h in histories if TRUSTED.search(h.get('author',{}).get('displayName',''))]
    cutoff=stamp(trusted[0]['created']) if trusted else None
    versions=[v['name'] for v in f['versions']]
    if cutoff:
        for h in reversed(histories):
            if stamp(h['created'])<cutoff:continue
            for item in reversed(h['items']):
                name=item['field'].lower()
                if name in ('summary','description','environment'):f[name]=item.get('fromString') or ''
                if name in ('version','versions','affects version/s'):
                    # Jira version events add/remove a single value, not a whole list.
                    old,new=item.get('fromString'),item.get('toString')
                    if new in versions:versions.remove(new)
                    if old and old not in versions:versions.insert(0,old)
    comments=[]; uncertainty=[]
    if not cutoff:uncertainty.append('No trusted-role edit identified; latest supplied report retained')
    for c in f.get('comment',{}).get('comments',[]):
        if cutoff and stamp(c['created'])>=cutoff:continue
        if TRUSTED.search(c.get('author',{}).get('displayName','')):continue
        # Comment edit histories are unavailable; exclude post-cutoff edited bodies.
        if cutoff and stamp(c.get('updated',c['created']))>=cutoff:
            uncertainty.append('Excluded pre-cutoff comment edited after cutoff: historic body unavailable, id='+str(c.get('id','unknown')))
            continue
        comments.append(c['body'])
    if not versions:raise ValueError('No affected version: '+issue['key'])
    return {'id':issue['key'],'title':f['summary'],'description':f.get('description') or '',
            'environment':f.get('environment') or '', 'comments':comments,'versions':versions,
            'cutoff':cutoff.isoformat() if cutoff else None,'input_uncertainty':uncertainty}
def prepare(root):
    source=root/'data/source/bugcraft_bench';out=root/'data/inputs';out.mkdir(parents=True,exist_ok=True)
    cases=[];audit=[]
    for p in sorted(source.glob('*/issue.json')):
        case=normalize(json.loads(p.read_text()));cases.append(case)
        target=out/(case['id']+'.json');target.write_text(json.dumps(case,indent=2))
        audit.append({'id':case['id'],'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'cutoff':case['cutoff'],'uncertainty':case['input_uncertainty']})
    (out/'normalization-audit.json').write_text(json.dumps({'algorithm':'pre-first-trusted-role-v1','transform_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'cases':audit},indent=2))
    (out/'manifest.json').write_text(json.dumps({'count':len(cases),'ids':[c['id'] for c in cases]},indent=2))
    return cases
if __name__=='__main__':
    root=pathlib.Path(__file__).resolve().parents[1];print('Prepared',len(prepare(root)),'pre-triage inputs')
