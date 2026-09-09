import json,pathlib
from bugcraft_bench.pi_session import command,MODEL
from bugcraft_bench.guest import canonical
from bugcraft_bench.evidence import digest

def test_clean_policy(tmp_path):
    cmd=command(tmp_path,tmp_path/'attempt')
    assert cmd[cmd.index('--model')+1]==MODEL
    assert cmd[cmd.index('--thinking')+1]=='medium'
    for flag in ('--no-extensions','--no-skills','--no-context-files','--no-prompt-templates','--no-themes'):assert flag in cmd
    assert cmd.count('--extension')==cmd.count('--skill')==1
    assert '--system-prompt' not in cmd and '--append-system-prompt' not in cmd

def test_version_mapping():
    assert canonical('Minecraft 1.14.1 Pre-Release 1')=='1.14.1-pre1'
    assert canonical('1.20.5 Release Candidate 2')=='1.20.5-rc2'

def test_pinned_sources_and_normalization():
    root=pathlib.Path(__file__).resolve().parents[1]
    source=root/'data/source'
    manifest=json.loads((source/'manifest.json').read_text())
    assert len(manifest['files'])==86
    assert all(digest(source/f['path'])==f['sha256'] for f in manifest['files'])
    audit=json.loads((root/'data/inputs/normalization-audit.json').read_text())
    assert len(audit['cases'])==86
    assert all(digest(root/'data/inputs'/(c['id']+'.json'))==c['input_sha256'] for c in audit['cases'])
    assert digest(root/'bugcraft_bench/dataset.py')==audit['transform_sha256']

def test_evaluation_has_time_limit_without_turn_cap():
    import inspect
    from bugcraft_bench import pi_session
    signature=inspect.signature(pi_session.run)
    assert signature.parameters['timeout'].default==1200
    assert 'max_turns' not in signature.parameters
    assert "return 'turn_limit'" not in inspect.getsource(pi_session.run)
    runner=(pathlib.Path(__file__).resolve().parents[1]/'bugcraft_bench/runner.py').read_text()
    assert 'Time limit: 20 minutes. There is no assistant-turn limit.' in runner
    assert '30 assistant turns' not in runner
