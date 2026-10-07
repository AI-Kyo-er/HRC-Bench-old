from hrc_pilot.joint_resource_use import resource_use_evidence


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
