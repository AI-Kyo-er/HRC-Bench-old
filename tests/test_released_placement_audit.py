import json

import pytest

from hrc_pilot.released_placement_audit import (
    released_placement_records,validate_target_definition,audit_run,render_released_placement_audit)


def state(t,held=None,carried=(),robot_contact=False):
    return {'time_s':t,'objects':{'food':[0,0,1],'bowl':[0,0,1]},
        'human_execution':{'held_object':held,'carried_objects':list(carried)},
        'contacts':[{'geom1':'food_g0','geom2':'gripper_left'}] if robot_contact else []}


def placement(t,geometry=True):
    # 复现已知缺口：原生记录宣称释放，但执行器仍明确持物。
    return {'time_s':t,'native_geometry_satisfied':geometry,'receiver_contact':True,
        'released':True,'object_speed_m_s':0.,'receiver_speed_m_s':0.,
        'released_stable_placement':True}


def test_held_success_does_not_transfer_old_stability_to_release():
    trace=[state(0,'food'),state(.1,'food'),state(.2),state(.3)]
    result=released_placement_records(trace,[placement(t) for t in [.1,.2,.3]],'food','bowl')
    assert [r['released_stable_placement'] for r in result]==[False,False,True]
    assert result[0]['human_owned_required_objects']==['food']
    assert result[1]['recomputed_stable_duration_s']==pytest.approx(.1)


def test_carried_payload_is_owned_even_when_another_object_is_held():
    trace=[state(0),state(.2,'bowl',['food','bowl'])]
    result=released_placement_records(trace,[placement(.2)],'food','bowl')
    assert not result[0]['required_objects_released']


def test_required_receiver_release_and_robot_contact_are_separate_constraints():
    trace=[state(0),state(.2,'bowl',['bowl']),state(.4,robot_contact=True),state(.6)]
    result=released_placement_records(trace,[placement(t) for t in [.2,.4,.6]],
        'food','bowl',['food','bowl'])
    assert [r['released_stable_placement'] for r in result]==[False,False,True]
    assert result[1]['required_objects_with_actual_hand_contact']==['food']


def test_relation_loss_resets_stability_and_attribution_is_not_inferred():
    trace=[state(t) for t in [0,.1,.2,.3,.4]]
    result=released_placement_records(trace,[placement(.1),placement(.2,False),
        placement(.3),placement(.4)],'food','bowl')
    assert [r['released_stable_placement'] for r in result]==[False,False,False,True]
    assert all('robot_contribution_score' not in row for row in result)


def test_unknown_payload_ownership_and_misaligned_time_fail_closed():
    trace=[state(0),state(.2)];del trace[-1]['human_execution']['carried_objects']
    with pytest.raises(ValueError,match='归属'):
        released_placement_records(trace,[placement(.2)],'food','bowl')
    with pytest.raises(ValueError,match='时间轴'):
        released_placement_records([state(0),state(.2)],[placement(.3)],'food','bowl')


def test_cannot_apply_food_goal_predicate_to_another_existing_object():
    task={'public_activity':{'scene_case':'food_into_bowl'},
          'native_robot_task':'put the cream cheese in the bowl'}
    validate_target_definition(task,'cream_cheese_1','akita_black_bowl_1')
    with pytest.raises(ValueError,match='公开目标'):
        validate_target_definition(task,'wine_bottle_1','akita_black_bowl_1')
    task={'native_placement_goal':{'kind':'on','object_id':'new_item','receiver_id':'new_shelf'}}
    validate_target_definition(task,'new_item','new_shelf')


def write_run(root):
    (root/'episode').mkdir()
    files={'summary.json':{'episodes':[{}]},'provenance.json':{'steps':2},
        'interaction_verification.json':{'status':'verified'},
        'independent_video_verification.json':{'status':'verified'},
        'episode/task.json':{'native_placement_goal':{'kind':'in','object_id':'food','receiver_id':'bowl'}}}
    for name,value in files.items():(root/name).write_text(json.dumps(value))
    (root/'episode/trace.jsonl').write_text('\n'.join(json.dumps(state(t)) for t in [0,.1,.2]))
    (root/'episode/placement_evidence.jsonl').write_text('\n'.join(json.dumps(placement(t)) for t in [.1,.2]))


def test_verified_flags_do_not_override_interruption_or_missing_terminal_steps(tmp_path):
    write_run(tmp_path)
    (tmp_path/'failure.json').write_text('{}')
    with pytest.raises(ValueError,match='中断'):
        audit_run(tmp_path,'food','bowl')
    (tmp_path/'failure.json').unlink()
    (tmp_path/'provenance.json').write_text(json.dumps({'steps':3}))
    with pytest.raises(ValueError,match='完整预定步数'):
        audit_run(tmp_path,'food','bowl')


def test_saved_release_report_is_rejected_when_source_changes(tmp_path):
    write_run(tmp_path)
    result=audit_run(tmp_path,'food','bowl')
    assert result['robot_contribution_score'] is None and result['formal_benchmark_score'] is None
    (tmp_path/'released_placement_audit.json').write_text(json.dumps(result))
    assert '0.2秒' in render_released_placement_audit(tmp_path)
    source=tmp_path/'episode/trace.jsonl';source.write_text(source.read_text()+'\n')
    with pytest.raises(ValueError,match='来源或分析'):
        render_released_placement_audit(tmp_path)
