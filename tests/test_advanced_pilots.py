import glob, json
from pathlib import Path
import pytest
from english_master.schema_validation import validate_instance

@pytest.mark.parametrize('level', ['b2','c1','c2'])
def test_pilot_artifacts(level):
    root=Path(f'curriculum/{level}-pilot/v1')
    content=json.loads((root/'content-input.json').read_text())
    assert len(content['lessons']) == 10
    validate_instance(content, f'{level}-pilot-content-input')
    run=next(p for p in (root/'runs').iterdir() if p.is_dir())
    manifest=json.loads((run/'manifest.json').read_text())
    validate_instance(manifest, f'{level}-pilot-manifest')
    assert len(manifest['inventory']) == 10
    for item in manifest['inventory']:
        packet=json.loads((run/item['path']).read_text())
        validate_instance(packet, f'{level}-pilot-lesson-packet')
        assert packet['content_status']=='UNREVIEWED'
        assert set(packet['prompts']) == {'listening','speaking','pronunciation','writing'}
