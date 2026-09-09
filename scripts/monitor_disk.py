#!/usr/bin/env python3
"""Watch only benchmark VMs; stop all lanes at a 20-GiB free-space watermark."""
import datetime,json,pathlib,shutil,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
with (root/'reports/setup/disk-monitor.jsonl').open('a',buffering=1) as log:
    while True:
        free=shutil.disk_usage(root).free
        log.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'free_bytes':free})+'\n')
        if free<20*1024**3:
            config=root/'vm/lanes/config.json'
            names=[x['container'] for x in json.loads(config.read_text())['lanes']] if config.exists() else ['bugcraft-windows']
            subprocess.run(['docker','stop','-t','120',*names])
            log.write(json.dumps({'event':'vm_stopped_disk_watermark'})+'\n');break
        config=root/'vm/lanes/config.json'
        names=[x['container'] for x in json.loads(config.read_text())['lanes']] if config.exists() else ['bugcraft-windows']
        state=subprocess.run(['docker','inspect','-f','{{.State.Running}}',*names],capture_output=True,text=True)
        if 'true' not in state.stdout.splitlines():break
        time.sleep(15)
