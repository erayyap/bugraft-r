"""Fixed-command QEMU control. Only the benchmark guest is addressable."""
import json,os,pathlib,subprocess,time
from contextlib import contextmanager
import fcntl
from bugcraft_bench.lane import settings

ROOT=pathlib.Path(__file__).resolve().parents[1]
PROTOCOL='explicit-vm-pause-v1'
# QEMU HMP stays live while virtual CPUs are stopped (unlike Docker pause).
MONITOR=r'''
import socket,sys
command=sys.argv[1]
assert command in ('info status','stop','cont')
s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect('/dev/shm/monitor.sock')
def receive():
 data=b''
 while b'(qemu)' not in data:
  chunk=s.recv(65536)
  if not chunk:raise RuntimeError('Monitor disconnected')
  data+=chunk
 return data
receive();s.sendall((command+'\n').encode());print(receive().decode(errors='replace'));s.close()
'''
def monitor(command):
    if command not in ('info status','stop','cont'):raise ValueError('Unsupported VM operation')
    p=subprocess.run(['docker','exec',settings().container,'python3','-c',MONITOR,command],capture_output=True,text=True,timeout=10,check=True)
    return p.stdout

def state():
    output=monitor('info status')
    if 'VM status: running' in output:return 'running'
    if 'VM status: paused' in output:return 'paused'
    raise RuntimeError('Guest is neither running nor paused')

def set_state(desired):
    if desired not in ('running','paused'):raise ValueError('Invalid target state')
    before=state()
    if before!=desired:monitor('cont' if desired=='running' else 'stop')
    after=state()
    if after!=desired:raise RuntimeError('VM state transition not confirmed')
    target=os.environ.get('BUGCRAFT_VM_TIMING')
    if target:
        with open(target,'a') as f:f.write(json.dumps({'wall_time':time.time(),'before':before,'after':after,'protocol':PROTOCOL})+'\n')
    return after

@contextmanager
def serialized():
    path=settings(ROOT).lock;path.parent.mkdir(exist_ok=True)
    with path.open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)
