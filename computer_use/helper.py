#!/usr/bin/env python3
"""Generic RFB desktop input. No game/domain knowledge or evaluator access."""
import argparse,base64,io,json,sys,time,signal,pathlib,uuid,os
from vncdotool import api
from vncdotool.client import VNCDoToolFactory
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from computer_use import vm_pause
from bugcraft_bench.lane import settings
class WindowsFactory(VNCDoToolFactory):
    force_caps=True

def relative_pointer(dx,dy):
    control=settings().control
    ident=uuid.uuid4().hex
    tmp=control/'ui-request.tmp';tmp.write_text(json.dumps({'id':ident,'action':'move_relative','dx':dx,'dy':dy}));os.replace(tmp,control/'ui-request.json')
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        try:
            result=json.loads((control/'ui-response.json').read_text(encoding='utf-8-sig'))
            if result.get('id')==ident and result.get('ok'):return
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.05)
    raise RuntimeError('Relative input acknowledgement timed out')

def validate(a,width,height):
    action=a['action']
    if action not in ('screenshot','click','move','move_relative','drag','key','type','scroll','wait','pause_vm','resume_vm'):raise ValueError('Unknown action')
    required={'click':('x','y'),'move':('x','y'),'drag':('x','y','to_x','to_y'),'key':('keys',),'type':('text',),'scroll':('scroll',)}
    if any(k not in a for k in required.get(action,())):raise ValueError('Missing required action parameter')
    if action=='move_relative':
        if any(not isinstance(a.get(k),int) or abs(a[k])>500 for k in ('dx','dy')):raise ValueError('Relative deltas must be integers -500..500')
    for pair in [('x','y'),('to_x','to_y')]:
        if any(k in a for k in pair):
            x,y=(a[k] for k in pair)
            if not (isinstance(x,int) and isinstance(y,int) and 0<=x<width and 0<=y<height):raise ValueError('Coordinates outside screenshot')
    if not 0<=a.get('duration',0.1)<=5:raise ValueError('Duration must be 0..5 seconds')
    if len(a.get('text',''))>2000:raise ValueError('Text limited to 2000 characters')
    keys=a.get('keys',[])
    if len(keys)>8 or any(not isinstance(k,str) or not k or len(k)>30 for k in keys):raise ValueError('Invalid keys')
    if a.get('button',1) not in (1,2,3):raise ValueError('Invalid button')
    if not 1<=a.get('clicks',1)<=2:raise ValueError('Invalid click count')
    if not -10<=a.get('scroll',0)<=10:raise ValueError('Scroll must be -10..10')

def perform(client,a,capture=True):
    client.refreshScreen();width,height=client.screen.size;validate(a,width,height)
    action=a['action'];held=[];button=None
    try:
        if action=='pause_vm':vm_pause.set_state('paused')
        elif action=='resume_vm':vm_pause.set_state('running')
        if action in ('click','move','drag'):
            client.mouseMove(a['x'],a['y'])
        if action=='move_relative':relative_pointer(a['dx'],a['dy'])
        if action=='click':
            for _ in range(a.get('clicks',1)):
                client.mousePress(a.get('button',1));time.sleep(.08)
        elif action=='drag':
            button=a.get('button',1);client.mouseDown(button)
            client.mouseMove(a['to_x'],a['to_y']);time.sleep(a.get('duration',.2))
        elif action=='key':
            for k in a['keys']:client.keyDown(k);held.append(k)
            time.sleep(a.get('duration',.1))
        elif action=='type':
            for ch in a['text']:
                client.keyPress(ch);time.sleep(.02)
        elif action=='scroll':
            for _ in range(abs(a['scroll'])):client.mousePress(4 if a['scroll']>0 else 5)
        elif action=='wait':time.sleep(a.get('duration',1))
    finally:
        for k in reversed(held):client.keyUp(k)
        if button is not None:client.mouseUp(button)
    time.sleep(.15)
    return screenshot(client) if capture else {}

def screenshot(client):
    client.refreshScreen()
    image=io.BytesIO();client.screen.save(image,format='PNG')
    return {'width':client.screen.width,'height':client.screen.height,'image':base64.b64encode(image.getvalue()).decode()}

def batch_steps(a,width,height):
    steps=a.get('actions') if a.get('action')=='batch' else [a]
    if not isinstance(steps,list) or not 1<=len(steps)<=16:raise ValueError('Batch requires 1-16 actions')
    for step in steps:validate(step,width,height)
    if a.get('action')=='batch':
        duration=sum(s.get('duration',1 if s['action']=='wait' else .1) + len(s.get('text',''))*.02 + .15 for s in steps)
        if duration>30:raise ValueError('Batch requested duration exceeds 30 seconds')
    return steps

def execute(client,a):
    client.refreshScreen();steps=batch_steps(a,*client.screen.size);log=[];error=None
    for index,step in enumerate(steps):
        try:
            current=vm_pause.state()
            if current=='paused' and step['action'] not in ('screenshot','pause_vm','resume_vm'):
                raise RuntimeError('VM is paused: use resume_vm before input or wait actions')
            perform(client,step,capture=False)
            log.append({'index':index,'action':step['action'],'status':'completed','vm_state':vm_pause.state()})
        except Exception as exc:
            error=type(exc).__name__+': '+str(exc)
            log.append({'index':index,'action':step['action'],'status':'failed','error':error})
            break
    result=screenshot(client);result.update(vm_state=vm_pause.state(),action_log=log)
    if error:result['error']=error
    return result

def main():
    def interrupted(*_):raise KeyboardInterrupt('Transport interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    a=json.load(sys.stdin)
    with vm_pause.serialized():
        with api.connect(settings().vnc,factory_class=WindowsFactory,timeout=15) as client:
            print(json.dumps(execute(client,a)))
if __name__=='__main__':main()
