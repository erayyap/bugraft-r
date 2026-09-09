import json
import threading
import time

from bugcraft_bench.guest import Guest


def test_state_retries_atomic_smb_replace(tmp_path):
    control = tmp_path / 'vm' / 'shared' / 'control'
    control.mkdir(parents=True)
    state = control / 'state.json'

    def publish():
        time.sleep(0.03)
        state.write_text(json.dumps({'game_running': False, 'games': []}))

    writer = threading.Thread(target=publish)
    writer.start()
    try:
        assert Guest(tmp_path).state()['games'] == []
    finally:
        writer.join(timeout=2)
