#!/usr/bin/env python3
"""Provision four overlays only from a cleanly stopped original VM."""
import json,pathlib,shutil,subprocess,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bugcraft_bench.evidence import atomic_json,utc
IMAGE='dockurr/windows@sha256:0cff9eb0e7aee9953e55bc682852ca4fdca233145a58ae1ec94f0b0c01a2ed30'
def call(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def inspect(name):
 p=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
 return json.loads(p.stdout)[0] if p.returncode==0 else None

def main():
 if shutil.disk_usage(ROOT).free<35*1024**3:raise RuntimeError('Need35GiB free before overlay provisioning')
 source=inspect('bugcraft-windows-archive')
 if source is None:
  source=inspect('bugcraft-windows')
  if not source or source['State']['Status']!='exited' or source['State']['ExitCode']!=0:raise RuntimeError('Original Windows must exit cleanly first')
  call(['docker','rename','bugcraft-windows','bugcraft-windows-archive'])
 else:
  if source['State']['Running']:raise RuntimeError('Archived backing disk is running: refuse')
 base=ROOT/'vm/storage';assert (base/'data.qcow2').exists()
 private=ROOT/'vm/private/vm.env'
 original=dict(line.split('=',1) for line in private.read_text().splitlines() if '=' in line)
 configs=[]
 dns=['1.1.1.1','8.8.8.8']
 for i in range(1,5):
  name='bugcraft-windows' if i==1 else f'bugcraft-windows-{i}'
  lane=ROOT/f'vm/lanes/lane-{i}';storage=lane/'storage';shared=lane/'shared'
  for p in (storage,shared,shared/'control',shared/'evidence',lane/'private'):p.mkdir(parents=True,exist_ok=True)
  (lane/'private').chmod(0o700);(shared/'control').chmod(0o700)
  for sourcefile in (ROOT/'vm/shared').iterdir():
   if sourcefile.is_file() and sourcefile.suffix in ('.ps1','.cs'):shutil.copy2(sourcefile,shared/sourcefile.name)
  # Firmware vars and identity files are writable copies; data backing is not.
  for filename in ('windows.rom','windows.vars','windows.ver','windows.base','windows.boot'):
   if not (storage/filename).exists():shutil.copy2(base/filename,storage/filename)
  for iso in base.glob('*.iso'):
   link=storage/iso.name
   if not link.is_symlink() and not link.exists():link.symlink_to('/base/'+iso.name)
  (storage/'windows.mac').write_text(f'02:BC:00:00:00:{i:02X}\n')
  disk=storage/'data.qcow2'
  if not disk.exists():
   call(['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{base}:/base:ro','-v',f'{storage}:/storage','--entrypoint','/usr/bin/qemu-img',IMAGE,'create','-f','qcow2','-F','qcow2','-b','/base/data.qcow2','/storage/data.qcow2'])
  env=original|{'RAM_SIZE':'8G','CPU_CORES':'4','DISK_SIZE':'48G','DISK_FMT':'qcow2'}
  envpath=lane/'private/vm.env';envpath.write_text('\n'.join(f'{k}={v}' for k,v in env.items())+'\n');envpath.chmod(0o600)
  info=inspect(name)
  if info is None:
   cmd=['docker','run','-d','--name',name,'--device=/dev/kvm','--device=/dev/net/tun','--cap-add','NET_ADMIN','--env-file',str(envpath),'--cpus','4','--memory','11g','--memory-swap','11g','--log-opt','max-size=10m','--log-opt','max-file=2','--stop-timeout','120','-p',f'127.0.0.1:{8005+i}:8006','-p',f'127.0.0.1:{5909+i}:5900','-v',f'{storage}:/storage','-v',f'{base}:/base:ro','-v',f'{shared}:/shared','-v',f'{ROOT}/vm/shared/tools:/shared/tools:ro']
   for server in dns:cmd+=['--dns',server]
   call(cmd+[IMAGE])
  elif not info['State']['Running']:call(['docker','start',name])
  configs.append({'id':i,'container':name,'ram_gib':8,'vcpus':4,'web_port':8005+i,'vnc_published_port':5909+i,'vnc_tunnel_port':5920+i,'storage':str(storage.relative_to(ROOT)),'shared':str(shared.relative_to(ROOT)),'backing':'vm/storage/data.qcow2','backing_mount_readonly':True,'mac':f'02:BC:00:00:00:{i:02X}'})
 atomic_json(ROOT/'vm/lanes/config.json',{'created_utc':utc(),'image':IMAGE,'archive_container':'bugcraft-windows-archive','lanes':configs,'secret_images':'Backing/overlay disks contain private account state; do not publish.'})
 print('Four containers launched; guest readiness is not yet verified.',flush=True)
if __name__=='__main__':main()
