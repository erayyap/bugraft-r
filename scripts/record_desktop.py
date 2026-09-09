#!/usr/bin/env python3
"""Bounded low-rate video; explicit capture failure file; no auth/setup recording."""
import argparse,io,json,pathlib,subprocess,time,shutil,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from bugcraft_bench.lane import settings
from vncdotool import api
p=argparse.ArgumentParser();p.add_argument('output',type=pathlib.Path);p.add_argument('--seconds',type=int,default=1200);a=p.parse_args()
start=time.monotonic();frames=0;error=None
encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-f','image2pipe','-vcodec','png','-framerate','2','-i','-','-an','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-b:v','300k','-maxrate','500k','-bufsize','1M','-t',str(a.seconds),'-y',str(a.output)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    with api.connect(settings().vnc,timeout=15) as client:
        while time.monotonic()-start<a.seconds and not a.output.with_suffix('.stop').exists():
            if shutil.disk_usage(a.output.parent).free<20*1024**3:raise RuntimeError('disk_watermark')
            then=time.monotonic();buf=io.BytesIO();client.captureScreen(buf,format='PNG');encoder.stdin.write(buf.getvalue());encoder.stdin.flush();frames+=1
            time.sleep(max(0,.5-(time.monotonic()-then)))
except Exception as exc:error=type(exc).__name__+': '+str(exc)
finally:
    encoder.stdin.close();code=encoder.wait(timeout=30)
    if code:error='encoder_failed: '+encoder.stderr.read().decode()[-1000:]
    a.output.with_suffix('.json').write_text(json.dumps({'fps_target':2,'frames':frames,'elapsed_seconds':time.monotonic()-start,'capture_error':error,'encoder_returncode':code,'bitrate':'300k','maxrate':'500k'},indent=2))
