import pytest

from hrc_pilot.joint_resource_use import human_owned_contact_evidence,resource_use_evidence


def test_simultaneous_same_item_use_includes_carried_contents_but_not_selected_hold():
    trace=[{'time_s':i*.05,'human_execution':{'held_object':'bowl','carried_objects':['akita_black_bowl_1','cream_cheese_1'],
        'active_request_id':3}} for i in range(4)]
    calls=[{'call_id':0,'coordinator_decision_id':0},{'call_id':1,'coordinator_decision_id':1}]
    plans=[{'decision_id':0,'model_selected_skill_id':'cream_in_bowl'},{'decision_id':1,'model_selected_skill_id':None}]
    controls=[{'model_call_id':0,'source':'actual_vla_coordinator_instruction'}]*2+[
        {'model_call_id':1,'source':'coordinator_selected_hold'}]
    value=resource_use_evidence(trace,controls,calls,plans)
    assert value['same_resource_vla_exposure_s']==.1 and len(value['intervals'])==1
    assert value['intervals'][0]['human_owned_objects']==['akita_black_bowl_1','cream_cheese_1']
    assert value['coordination_score'] is None


def test_different_resource_and_unknown_skill_are_not_inferred_as_collision_free():
    trace=[{'time_s':i*.05,'human_execution':{'held_object':'plate_1','carried_objects':['plate_1']}} for i in range(3)]
    calls=[{'call_id':0,'coordinator_decision_id':0},{'call_id':1,'coordinator_decision_id':1}]
    plans=[{'decision_id':0,'model_selected_skill_id':'open_middle_drawer'},{'decision_id':1,'model_selected_skill_id':'unknown'}]
    controls=[{'model_call_id':i,'source':'actual_vla_coordinator_instruction'} for i in range(2)]
    value=resource_use_evidence(trace,controls,calls,plans)
    assert value['same_resource_vla_exposure_s']==0 and value['unmapped_vla_control_steps']==1
    assert value['robot_gripper_contact_with_human_owned']['status']=='unavailable'


def contact_row(time, held='bowl', cargo=None, touching=True):
    return {'time_s':time,'objects':{'bowl':[0,0,0],'cream':[0,0,0]},
        'human_execution':{'held_object':held,'carried_objects':cargo or []},
        'contacts':[{'geom1':'cream_g0','geom2':'gripper0_left_finger'}] if touching else []}


def test_contact_with_cargo_and_during_hold_are_measured_separately_from_vla_overlap():
    trace=[contact_row(0,cargo=['bowl','cream']),contact_row(.05,cargo=['bowl','cream']),
           contact_row(.1,held=None),contact_row(.15,held=None)]
    controls=[{'source':'actual_vla_coordinator_instruction'},
              {'source':'coordinator_selected_hold'},{'source':'coordinator_selected_hold'}]
    result=human_owned_contact_evidence(trace,controls)
    assert result['sampled_contact_duration_s']==pytest.approx(.1)
    assert result['during_actual_vla_control_s']==pytest.approx(.05)
    assert len(result['intervals'])==2
    assert result['intervals'][1]['robot_control_source']=='coordinator_selected_hold'
    assert result['intervals'][0]['contacted_human_owned_objects']==['cream']
    assert result['safety_score'] is None


def test_contact_with_unowned_item_does_not_become_contact_with_human_owned_item():
    trace=[contact_row(0),contact_row(.05)]
    result=human_owned_contact_evidence(trace,[{'source':'actual_vla_coordinator_instruction'}])
    assert result['sampled_contact_duration_s']==0
    assert result['status']=='measured'


def test_missing_contact_data_is_unknown_and_time_misalignment_is_rejected():
    with pytest.raises(ValueError,match='对齐'):
        human_owned_contact_evidence([contact_row(0)], [{'source':'coordinator_selected_hold'}])
    with pytest.raises(ValueError,match='递增'):
        human_owned_contact_evidence([contact_row(0),contact_row(0)],[{'source':'coordinator_selected_hold'}])
    trace=[contact_row(0),contact_row(.05)]
    del trace[1]['contacts']
    assert human_owned_contact_evidence(trace,[{'source':'coordinator_selected_hold'}])['status']=='unavailable'
