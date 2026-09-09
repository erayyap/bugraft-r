from pathlib import Path
import pytest
from bugcraft_bench.lane import settings

def test_legacy_defaults_unchanged(monkeypatch,tmp_path):
 monkeypatch.delenv('BUGCRAFT_LANE',raising=False)
 lane=settings(tmp_path)
 assert lane.container=='bugcraft-windows'
 assert lane.control==tmp_path/'vm/shared/control'
 assert lane.vnc=='127.0.0.1::5901'

def test_four_lanes_are_separate(monkeypatch,tmp_path):
 lanes=[]
 for i in range(1,5):
  monkeypatch.setenv('BUGCRAFT_LANE',str(i));lanes.append(settings(tmp_path))
 for attr in ('container','control','vnc','lock'):
  assert len({getattr(l,attr) for l in lanes})==4
 assert lanes[0].container=='bugcraft-windows'
 assert lanes[-1].vnc=='127.0.0.1::5924'

@pytest.mark.parametrize('value',['0','5','../x','foo','1;shutdown'])
def test_bad_lane_rejected(monkeypatch,tmp_path,value):
 monkeypatch.setenv('BUGCRAFT_LANE',value)
 with pytest.raises(ValueError):settings(tmp_path)
