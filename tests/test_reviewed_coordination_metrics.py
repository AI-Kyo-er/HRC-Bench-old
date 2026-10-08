import json

import pytest

from hrc_pilot.reviewed_coordination_metrics import reviewed_metrics


def fixture(tmp_path):
    ep=tmp_path/'episode';ep.mkdir()
    for name in ['interaction_verification.json','independent_video_verification.json']:
        (tmp_path/name).write_text(json.dumps({'status':'verified'}))
    (tmp_path/'summary.json').write_text('{}')
    values={'trace.jsonl':[{'time_s':t} for t in [0.,.05,.1,.15]],
        'robot_control.jsonl':[{'source':'actual_vla_coordinator_instruction'},
                               {'source':'coordinator_selected_hold'}, {'source':'coordinator_selected_hold'}],
        'public_dialogue.jsonl':[{'time_s':.025,'speaker':'human','text':'Keep it here.'}],
        'robot_planner_io.jsonl':[{'time_s':.125,'decision':{'mode':'hold'}}]}
    for name,rows in values.items():(ep/name).write_text(''.join(json.dumps(row)+'\n' for row in rows))
    def anchor(file,row,pointer,value):return {'file':'episode/'+file,'row':row,'pointer':pointer,'equals':value}
    review={'review_type':'assistant_review_of_saved_records_not_human_study','reviewed_intervals':[{
        'label':'公开线索至所审阅回应','interpretation':'测试的是源时间段，不认证回应有效。',
        'start':anchor('public_dialogue.jsonl',0,'/time_s',.025),
        'end':anchor('robot_planner_io.jsonl',0,'/time_s',.125),
        'evidence':[anchor('robot_planner_io.jsonl',0,'/decision/mode','hold')]}]}
    (tmp_path/'coordination_process_review.json').write_text(json.dumps(review))
    return review


def test_source_times_and_partially_overlapping_controls_are_measured_without_semantic_score(tmp_path):
    fixture(tmp_path);result=reviewed_metrics(tmp_path);span=result['reviewed_intervals'][0]
    assert span['elapsed_sim_s']==pytest.approx(.1)
    assert span['actual_vla_control_s']==pytest.approx(.025)
    assert span['selected_hold_control_s']==pytest.approx(.075)
    assert result['formal_benchmark_score'] is None
    assert 'episode/robot_control.jsonl' in result['source_sha256']
    assert span['semantic_status']=='assistant_interpretation_not_independently_validated'


def test_private_notification_is_not_a_public_robot_response_start(tmp_path):
    review=fixture(tmp_path)
    review['reviewed_intervals'][0]['start']['file']='episode/private_context.jsonl'
    (tmp_path/'coordination_process_review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError,match='私人通知'):reviewed_metrics(tmp_path)


def test_changed_evidence_or_reversed_interval_cannot_silently_keep_a_positive_measurement(tmp_path):
    review=fixture(tmp_path)
    (tmp_path/'episode/robot_planner_io.jsonl').write_text(json.dumps({'time_s':.125,'decision':{'mode':'execute'}})+'\n')
    with pytest.raises(ValueError,match='不符'):reviewed_metrics(tmp_path)
    review['reviewed_intervals'][0]['start']['equals']=.14
    (tmp_path/'episode/public_dialogue.jsonl').write_text(json.dumps({'time_s':.14})+'\n')
    (tmp_path/'coordination_process_review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError,match='起止'):reviewed_metrics(tmp_path)
