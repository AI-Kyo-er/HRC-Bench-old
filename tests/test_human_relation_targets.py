import json

import numpy as np
import pytest

from hrc_pilot.human_relation_targets import relation_placement_targets
from hrc_pilot.constrained_human_decision import decision_json_schema,parse_constrained_decision,PREFIX
from hrc_pilot.intent_observation import intent_observation
from hrc_pilot.relation_human_executor import RelationHumanExecutor
from test_human_owned_buffer import make_actor


def test_collision_reference_moves_target_and_tipping_removes_the_affordance():
    pytest.importorskip('robosuite')
    from robosuite.utils.binding_utils import MjSim
    sim=MjSim.from_xml_string('''<mujoco><worldbody>
    <body name="cup_main" pos=".1 .2 1"><freejoint/>
    <geom name="cup_bottom" type="box" size=".05 .05 .003"/></body>
    <body name="food_main" pos="0 0 1.1"><freejoint/>
    <geom name="food_box" type="box" size=".02 .02 .015"/></body>
    </worldbody></mujoco>''');sim.forward()
    target=relation_placement_targets(sim.model,sim.data,['cup','food'],{'cup':('in',)})['food__in__cup']
    np.testing.assert_allclose(target['target_xyz'],[.1,.2,1.022])
    assert target['relation']=='in' and target['support_collision_geom']=='cup_bottom'
    sim.data.qpos[:3]+=[.2,-.1,.1];sim.forward()
    new=relation_placement_targets(sim.model,sim.data,['cup','food'],{'cup':('in',)})['food__in__cup']
    np.testing.assert_allclose(np.asarray(new['target_xyz'])-target['target_xyz'],[.2,-.1,.1])
    sim.data.qpos[3:7]=[np.sqrt(.5),np.sqrt(.5),0,0];sim.forward()
    assert relation_placement_targets(sim.model,sim.data,['cup','food'],{'cup':('in',)})=={}


def test_relation_schema_keeps_source_identity_and_does_not_map_to_a_personal_table_point():
    scene={'objects_xyz':{'food':[],'cup':[]},'regions_xyz':{'food_personal':[], 'food__in__cup':[]},
           'relation_targets':{'food__in__cup':{'object_id':'food','relation':'in','reference_object_id':'cup'}}}
    call={'name':'choose_human_contribution','arguments':{'contribution':{'kind':'place_object',
         'object_id':'food','destination':'food__in__cup'},'communication':None}}
    raw=PREFIX+json.dumps(call)+'\n</tool_call>'
    choice,_,_=parse_constrained_decision(raw,scene)
    assert choice['destination']=='food__in__cup'
    call['arguments']['contribution']['object_id']='cup'
    with pytest.raises(ValueError):parse_constrained_decision(PREFIX+json.dumps(call)+'\n</tool_call>',scene)
    variants=decision_json_schema(scene)['properties']['arguments']['properties']['contribution']['anyOf']
    for variant in variants:
        prop=variant.get('properties',{})
        if prop.get('object_id',{}).get('enum')==['cup'] and 'destination' in prop:
            assert 'food__in__cup' not in prop['destination']['enum']


def test_idle_motion_is_not_reported_as_live_request_and_keeps_actor_identity():
    actor,_=make_actor(True);actor.__class__=RelationHumanExecutor;actor.cancelled_requests=[]
    actor.active_request=7;actor.last_request=9;actor.completed_requests=[7]
    actor.accepted_intent='wait'
    feedback=actor.public_feedback()
    assert feedback['active_request_id']==7 # 历史兼容字段
    assert feedback['active_motion_request_id'] is None and not feedback['motion_in_progress']
    scene={'time_s':10,'own_execution':feedback,'measured_world':{},'objects_xyz':{},'regions_xyz':{},
           'public_dialogue':[],'private_context':[],'action_interface':{}}
    own=intent_observation(scene)['own_execution']
    assert own['actor']=='human' and own['current_request_id'] is None and own['last_motion_request_id']==7
    assert own['last_received_request_id']==9


def test_unavailable_reference_blocks_selected_transfer_then_resumes_without_new_policy_choice():
    actor,data=make_actor(True);actor.__class__=RelationHumanExecutor;actor.cancelled_requests=[]
    dest='plate__on__cup';actor.regions[dest]=[.1,.2,1.]
    actor.env.env._hrc_region_accessibility={dest:False}
    actor.transfer_destination=dest;actor.phase='transfer_translate';actor.active_request=2
    actor.accepted_intent='relocate'
    actor.target=np.array([.1,.2,1.3])
    actor.physics_step()
    assert actor.phase=='relation_target_unavailable' and actor.held=='plate'
    assert actor.completed_requests==[] and actor.public_feedback()['execution_blocked_reason']=='reference_support_unavailable'
    actor.env.env._hrc_region_accessibility[dest]=True;actor.physics_step()
    assert actor.phase=='transfer_translate' and actor.active_request==2 and actor.held=='plate'
    assert all(row['robot_pose_writes']==0 for row in actor.records)


def test_new_explicit_contribution_supersedes_old_motion_and_wait_only_continues_it():
    actor,_=make_actor(True);actor.__class__=RelationHumanExecutor;actor.cancelled_requests=[]
    actor.phase='transfer_raise';actor.active_request=2;actor.transfer_destination='drawer'
    actor.accept_choice({'action':'wait'},3)
    assert actor.receipts[-1]['continues_motion_request_id']==2 and actor.cancelled_requests==[]
    actor.accept_choice({'action':'pick','object_id':'plate'},4)
    assert actor.receipts[-1]['superseded_motion_request_id']==2 and actor.cancelled_requests==[2]
    assert actor.public_feedback()['active_motion_request_id'] is None
