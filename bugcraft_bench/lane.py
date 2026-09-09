"""Host-selected VM lane routing. This is configuration, not an OS sandbox."""
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Lane:
    id: int
    container: str
    control: Path
    vnc: str
    lock: Path
    web_port: int

def settings(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parents[1]
    selected=os.environ.get('BUGCRAFT_LANE')
    if selected is None and (root/'vm/lanes/config.json').exists():selected='1'
    if selected is None:
        return Lane(0,'bugcraft-windows',root/'vm/shared/control','127.0.0.1::5901',root/'.runtime/computer-input.lock',8006)
    if selected not in ('1','2','3','4'):raise ValueError('BUGCRAFT_LANE must be 1, 2, 3 or 4')
    i=int(selected)
    return Lane(i,'bugcraft-windows' if i==1 else f'bugcraft-windows-{i}',root/f'vm/lanes/lane-{i}/shared/control',f'127.0.0.1::{5920+i}',root/f'.runtime/computer-input-lane-{i}.lock',8005+i)

def environment(lane_id):
    if str(lane_id) not in ('1','2','3','4'):raise ValueError('Lane must be 1, 2, 3 or 4')
    return {'BUGCRAFT_LANE':str(lane_id)}
