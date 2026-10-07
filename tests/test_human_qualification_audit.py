import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('qualification_audit',Path(__file__).resolve().parents[1]/'scripts/verify_neural_human_qualification.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def fixture(root):
    ep=root/'human_activity';ep.mkdir()
    def write(name,value):
        (ep/name).write_text(json.dumps(value) if name.endswith('.json') else ''.join(json.dumps(r)+'\n' for r in value))
    (root/'provenance.json').write_text(json.dumps({'source_files_changed_during_run':[]}))
    write('parking_control.json',[{'physics_time_s':i/20,'eef_xyz':[0,0,0],
        'action':[-.3,-.3,.3,0,0,0,-1]} for i in range(80)])
    write('trace.jsonl',[{'step':i,'physics_time_s':4+i/20,'robot_ee':[0,0,0]} for i in range(3)])
    write('stationary_robot_control.jsonl',[{'source':'calibrated_stationary_robot_no_model','action':[0.]*6+[-1.],
        'step':i,'pre_physics_time_s':4+i/20,'post_physics_time_s':4+(i+1)/20} for i in range(2)])
    write('model_calls.jsonl',[]);write('human_control.jsonl',[{'human_object_pose_writes':0}])
    write('human_policy_io.jsonl',[{'raw_output':'{}'}]);write('human_planner_io.jsonl',[{'raw_model_output':'{}'}])
    return ep


def test_reconstructs_stationary_controls_and_physics_clock(tmp_path):
    fixture(tmp_path)
    result=audit.verify(tmp_path)
    assert result['robot_neural_calls']==0 and result['human_activity_steps']==2


@pytest.mark.parametrize('tamper',['robot_motion','clock','pose_write','model_call','source_change'])
def test_rejects_false_qualification_evidence(tmp_path,tamper):
    ep=fixture(tmp_path)
    if tamper in {'robot_motion','clock'}:
        path=ep/'stationary_robot_control.jsonl';controls=audit.rows(path)
        if tamper=='robot_motion':controls[0]['action'][0]=.2
        else:controls[0]['post_physics_time_s']+=.2
        path.write_text(''.join(json.dumps(r)+'\n' for r in controls))
    elif tamper=='pose_write':(ep/'human_control.jsonl').write_text('{"human_object_pose_writes":1}\n')
    elif tamper=='model_call':(ep/'model_calls.jsonl').write_text('{"model":"neural_robot"}\n')
    else:(tmp_path/'provenance.json').write_text('{"source_files_changed_during_run":["changed.py"]}')
    with pytest.raises(AssertionError):audit.verify(tmp_path)
