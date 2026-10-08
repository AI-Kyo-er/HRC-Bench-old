from copy import deepcopy

import numpy as np
import pytest

from hrc_pilot.public_scene_measurements import public_scene_measurements


def record():
    return {'objects':{'cream':[.24,0,1.2],'bowl':[0,0,1.],'cabinet':[0,-.3,1.]},
            'human_execution':{'held_object':'bowl','carried_objects':['bowl']},
            'contacts':[{'geom1':'cream_g1','geom2':'gripper0_finger1_collision'},
                        {'geom1':'cream_g1','geom2':'cabinet_g1'}]}


def test_separation_and_actual_ownership_remain_visible_without_task_truth_or_private_intent():
    r=record();before=deepcopy(r);m=public_scene_measurements(r,['cream','bowl'])
    assert r==before
    relation=m['relative_object_measurements']['cream__relative_to__bowl']
    np.testing.assert_allclose(relation['source_minus_reference_xyz_m'],[.24,0,.2])
    assert relation['xy_distance_m']==.24 and relation['contact_observed'] is False
    assert m['objects']['bowl']['human_carried'] and not m['objects']['bowl']['released_from_hands']
    assert m['objects']['cream']['robot_gripper_contact'] and not m['objects']['cream']['released_from_hands']
    r.update(score=True,task_success=True,private_intention='serve snack',future_context='cancel')
    assert public_scene_measurements(r,['cream','bowl'])==m
    assert not {'contained','ready','next_action','task_success','score'}.intersection(relation)


def test_contents_carried_with_container_are_not_claimed_released():
    r=record();r['human_execution']['carried_objects']=['bowl','cream'];r['contacts']=[]
    m=public_scene_measurements(r,['cream','bowl'])
    assert m['objects']['cream']['human_carried'] and not m['objects']['cream']['released_from_hands']
    r['human_execution']={'held_object':None,'carried_objects':[]}
    r['contacts']=[{'geom1':'bowl_g1','geom2':'cream_g1'}]
    m=public_scene_measurements(r,['cream','bowl'])
    assert m['objects']['cream']['released_from_hands']
    assert m['relative_object_measurements']['cream__relative_to__bowl']['contact_observed']
    assert m['relative_object_measurements']['bowl__relative_to__cream']['contact_observed']
    # 有接触的物品仍可水平相距24cm，测量不会替模型宣布容器内关系成立。
    assert m['relative_object_measurements']['cream__relative_to__bowl']['xy_distance_m']==.24


def test_missing_contact_measurements_are_unknown_rather_than_zero():
    r=record();r.pop('contacts');m=public_scene_measurements(r,['cream','bowl'])
    assert not m['contact_measurement_available']
    assert m['objects']['cream']['robot_gripper_contact'] is None
    assert m['objects']['cream']['released_from_hands'] is None
    assert m['relative_object_measurements']['cream__relative_to__bowl']['contact_observed'] is None


def test_invalid_or_unknown_objects_fail_instead_of_silently_producing_a_scene():
    r=record()
    for names in [['cream','hidden'],['cream','cream']]:
        with pytest.raises(ValueError):public_scene_measurements(r,names)
    r['objects']['cream']=[float('nan'),0,1]
    with pytest.raises(ValueError):public_scene_measurements(r,['cream','bowl'])


def test_complete_measurements_enter_actual_model_payload_and_later_tool_feedback_with_legacy_preserved():
    import json
    from hrc_pilot.joint_activity import ACTIVITIES
    from hrc_pilot.joint_world import observable_world
    from hrc_pilot.intent_observation import intent_observation
    from hrc_pilot.reasoning_constrained_human import ReasoningConstrainedHumanPolicy
    from hrc_pilot.constrained_human_decision import PREFIX
    from hrc_pilot.tool_joint_human import execution_tool_result
    r=record();r.update(time_s=0.,robot_qpos=[0]*9,human_body_xy=[.25,.6])
    regions={'cream_personal':[.2,.4,1.],'bowl_personal':[.1,.4,1.]}
    world=observable_world(r,regions,measurement_version=3)
    scene={'time_s':0.,'objects_xyz':r['objects'],'regions_xyz':regions,
           'own_execution':{'held_object':'bowl','phase':'idle'},'measured_world':world,
           'public_dialogue':[],'private_context':[],'action_interface':{}}
    received=[]
    def generate(payload):
        received.append(json.loads(payload))
        return PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
            'contribution':{'kind':'wait'},'communication':None}})+'\n</tool_call>'
    human=ReasoningConstrainedHumanPolicy(ACTIVITIES['snack_service'],model_path='/unused',generator=generate)
    row=human.decide(scene)
    actual=json.loads(received[-1]['messages'][-1]['content'])['scene']
    assert actual['measured_scene_geometry_and_contact']==world['public_scene_measurements']
    assert row['private_input']['scene']==actual and row['parse_error'] is None
    scene['time_s']=4.;human.decide(scene)
    tool=json.loads(next(m['content'] for m in received[-1]['messages'] if m['role']=='tool'))
    assert tool['measured_scene_geometry_and_contact']==world['public_scene_measurements']
    # 旧观测的工具历史和token输入保持原结构，不倒改已有运行。
    legacy=deepcopy(scene);legacy['measured_world']=observable_world(r,regions,measurement_version=2)
    assert 'measured_scene_geometry_and_contact' not in intent_observation(legacy)
    assert 'measured_scene_geometry_and_contact' not in execution_tool_result(0,legacy)
