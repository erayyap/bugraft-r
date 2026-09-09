#!/usr/bin/env python3
"""Start only our bounded Windows Enterprise evaluation VM; no activation changes."""
import json, pathlib, secrets, shutil, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
IMAGE='dockurr/windows@sha256:0cff9eb0e7aee9953e55bc682852ca4fdca233145a58ae1ec94f0b0c01a2ed30'
if shutil.disk_usage(ROOT).free < 80*1024**3: raise SystemExit('Require 80 GiB free before provisioning')
private=ROOT/'vm/private'; private.mkdir(parents=True,exist_ok=True); private.chmod(0o700)
env=private/'vm.env'
if not env.exists():
    env.write_text('VERSION=10e\nRAM_SIZE=12G\nCPU_CORES=6\nDISK_SIZE=48G\nDISK_FMT=qcow2\nUSERNAME=Benchmark\nPASSWORD='+secrets.token_urlsafe(24)+'\n')
    env.chmod(0o600)
for name in ['storage','shared','oem']: (ROOT/'vm'/name).mkdir(parents=True,exist_ok=True)
cmd=['docker','run','-d','--name','bugcraft-windows','--device=/dev/kvm','--device=/dev/net/tun','--cap-add','NET_ADMIN','--env-file',str(env),'--cpus','6','--memory','16g','--memory-swap','16g','--log-opt','max-size=10m','--log-opt','max-file=2','-p','127.0.0.1:8006:8006','-p','127.0.0.1:5900:5900','--stop-timeout','120']
for name,dest in [('storage','storage'),('shared','shared'),('oem','oem')]:cmd+=['-v',f'{ROOT}/vm/{name}:/{dest}']
subprocess.run(cmd+[IMAGE],check=True)
(ROOT/'reports/setup/vm-config.json').write_text(json.dumps({'image':IMAGE,'version':'Windows 10 Enterprise evaluation','ram_gib':12,'cores':6,'disk_virtual_gib':48,'host_min_free_gib':20,'network':'loopback exposed ports only','activation':'none'},indent=2))
