import importlib.util
import json
from pathlib import Path

import pytest


spec=importlib.util.spec_from_file_location('area_batch',Path(__file__).parents[1]/'scripts/run_area_feedback_batch.py')
batch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def complete(root):
    values={'batch_condition.json':{'condition':{'run':'sample'},'condition_table_sha256':'same'},
            'interaction_verification.json':{'status':'verified'},
            'independent_video_verification.json':{'status':'verified'},
            'joint_process_evidence.json':{'status':'audited'},
            'summary.json':{'episodes':[{}]},
            'provenance.json':{'source_files_changed_during_run':[]}}
    for name,value in values.items():(root/name).write_text(json.dumps(value))


def test_resume_accepts_same_verified_condition_without_writing(tmp_path):
    complete(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    batch.verified_existing_condition(tmp_path,{'run':'sample'},'same')
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('settings',[{'human_model':'/different','human_carried_observation':False},
                                    {'human_model':None,'human_carried_observation':True}])
def test_resume_cannot_skip_an_old_result_when_model_or_observation_method_changes(tmp_path,settings):
    complete(tmp_path)
    with pytest.raises(ValueError,match='方法配置不同'):
        batch.verified_existing_condition(tmp_path,{'run':'sample'},'same',settings)


@pytest.mark.parametrize('change',['condition','digest','video','missing','failure','source'])
def test_resume_rejects_mismatched_unverified_and_failed_results(tmp_path,change):
    complete(tmp_path)
    row={'run':'other' if change=='condition' else 'sample'}
    digest='different' if change=='digest' else 'same'
    if change=='video':(tmp_path/'independent_video_verification.json').write_text('{"status":"failed"}')
    if change=='missing':(tmp_path/'summary.json').unlink()
    if change=='failure':(tmp_path/'failure.json').write_text('{}')
    if change=='source':(tmp_path/'provenance.json').write_text('{"source_files_changed_during_run":["runtime.py"]}')
    with pytest.raises((ValueError,FileNotFoundError)):
        batch.verified_existing_condition(tmp_path,row,digest)
