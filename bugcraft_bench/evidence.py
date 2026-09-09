import datetime,hashlib,json,os,pathlib,re,shutil
SECRET=re.compile(r'(?i)(access_?token|refresh_?token|client_secret|authorization|password)([\s"\x27:=]+)([^\s,"\x27}]+)')
JWT=re.compile(r'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
def redact(text):
    text=re.sub(r'(?i)Bearer\s+[^\s"\x27]+','Bearer [REDACTED]',text)
    text=SECRET.sub(lambda m:m[1]+m[2]+'[REDACTED]',text)
    text=JWT.sub('[REDACTED]',text)
    text=re.sub(r'(?i)https?://(?:login\.(?:live|microsoftonline)\.com|microsoft\.com/devicelogin)[^\s"\x27]*','[AUTH_URL_EXCLUDED]',text)
    text=re.sub(r'Setting user: .*','Setting user: [REDACTED]',text)
    return text

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic_json(path,value):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2));os.replace(tmp,path)
def disk_guard(path,min_gib=20):
    if shutil.disk_usage(path).free<min_gib*1024**3:raise RuntimeError('Evidence disk watermark reached')
def digest(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
