#!/usr/bin/env python3
"""Public unmodified Prism, Temurin Java, Mesa software OpenGL for guest setup."""
import concurrent.futures,json,pathlib,urllib.request,hashlib
root=pathlib.Path(__file__).resolve().parents[1]/'vm/shared/tools';root.mkdir(parents=True,exist_ok=True)
def get(url):
    with urllib.request.urlopen(url,timeout=180) as r:return r.read()
def task(name,url):
    p=root/name
    if not p.exists():p.write_bytes(get(url))
    return {'name':name,'url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
prism=json.loads(get('https://api.github.com/repos/PrismLauncher/PrismLauncher/releases/tags/11.1.0'))
mesa=json.loads(get('https://api.github.com/repos/pal1000/mesa-dist-win/releases/tags/26.2.0'))
jobs=[('prism.zip',next(a['browser_download_url'] for a in prism['assets'] if a['name']=='PrismLauncher-Windows-MinGW-w64-Portable-11.1.0.zip')),('mesa.7z',next(a['browser_download_url'] for a in mesa['assets'] if a['name']=='mesa3d-26.2.0-release-msvc.7z'))]
for version in [8,17,21]:
    j=json.loads(get(f'https://api.github.com/repos/adoptium/temurin{version}-binaries/releases/latest'))
    asset=next(a for a in j['assets'] if a['name'].startswith('OpenJDK'+str(version)+'U-jre_x64_windows_hotspot_') and a['name'].endswith('.zip'))
    jobs.append((f'java{version}.zip',asset['browser_download_url']))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: records=list(pool.map(lambda pair:task(*pair),jobs))
(root/'manifest.json').write_text(json.dumps(records,indent=2));print('Guest tool downloads complete')
