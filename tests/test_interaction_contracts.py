from hrc_pilot.interaction_contracts import CONTRACTS,validate_contracts


def test_contracts_have_cross_agent_dependencies_and_private_information_is_not_public_truth():
    assert validate_contracts()
    assert len(CONTRACTS)==3
    for c in CONTRACTS.values():
        public=c.public()
        assert 'private_background' not in public['activity']
        assert 'external_context' not in public['activity']
        assert 'human_private_information' not in public
        assert 'evidence_requirements' not in public
        assert public['questions_that_can_be_resolved_by_interaction']
        assert public['activity']['dependencies']
        assert not {'next_action','stage','schedule','score','task_success'}.intersection(public)


def test_fixed_fixture_can_be_indicated_but_cannot_be_selected_for_pick_or_placement():
    import json
    import pytest
    from hrc_pilot.constrained_human_decision import PREFIX,parse_constrained_decision,decision_json_schema
    scene={'objects_xyz':{'cream':[],'cabinet':[]},'regions_xyz':{'staging':[]},'movable_object_ids':['cream']}
    def call(kind,obj):return PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
        'contribution':{'kind':kind,'object_id':obj,**({'destination':'staging'} if kind=='place_object' else {})},
        'communication':None}})+'\n</tool_call>'
    choice,_,_=parse_constrained_decision(call('indicate_object','cabinet'),scene)
    assert choice['action']=='point' and choice['object_id']=='cabinet'
    for kind in ['hold_object','place_object']:
        with pytest.raises(ValueError):parse_constrained_decision(call(kind,'cabinet'),scene)
    variants=decision_json_schema(scene)['properties']['arguments']['properties']['contribution']['anyOf']
    for v in variants:
        properties=v.get('properties',{})
        if properties.get('kind',{}).get('enum') in [['hold_object'],['place_object']]:
            assert 'cabinet' not in properties['object_id']['enum']


def test_relation_summary_exposes_missing_food_and_unknown_contacts_without_task_truth():
    from hrc_pilot.public_scene_measurements import public_scene_measurements
    from hrc_pilot.scene_relation_summary import scene_relation_summary
    record={'objects':{'bowl':[0,0,1],'cream':[.24,0,1.1]},
        'human_execution':{'held_object':None,'carried_objects':[]},'contacts':[]}
    m=public_scene_measurements(record,['bowl','cream'])
    summary=scene_relation_summary(m,{'bowl':('in',)})
    assert summary['reference_relations']['bowl']['observed_supported_items']==[]
    record['objects']['cream']=[.001,0,1.03]
    record['contacts']=[{'geom1':'bowl_g1','geom2':'cream_g1'},
                        {'geom1':'cream_g1','geom2':'gripper0_finger1_collision'}]
    summary=scene_relation_summary(public_scene_measurements(record,['bowl','cream']),{'bowl':('in',)})
    item=summary['reference_relations']['bowl']['observed_supported_items'][0]
    assert item['robot_gripper_contact'] and not item['released_from_hands']
    assert not {'ready','score','task_success','next_action'}.intersection(summary)
    record.pop('contacts')
    summary=scene_relation_summary(public_scene_measurements(record,['bowl','cream']),{'bowl':('in',)})
    assert summary['reference_relations']['bowl']['observed_supported_items'] is None


def test_execution_rejects_non_movable_or_unreachable_pickup_without_pose_changes():
    import numpy as np
    from hrc_pilot.contract_human_executor import ContractHumanExecutor
    from test_human_owned_buffer import make_actor
    actor,data=make_actor(True);actor.__class__=ContractHumanExecutor;actor.cancelled_requests=[]
    original=data.qpos.copy()
    actor.accept_choice({'action':'relocate','object_id':'cabinet','destination':'drawer'},1)
    assert actor.receipts[-1]['error']=='object_not_movable_by_human'
    data.qpos[13:16]=[2,0,.1];outside=data.qpos.copy()
    actor.accept_choice({'action':'pick','object_id':'cream'},2)
    assert actor.receipts[-1]['error']=='object_outside_declared_pickup_workspace'
    np.testing.assert_array_equal(data.qpos,outside)
    assert actor.held=='plate' and actor.completed_requests==[]


def test_contract_facts_and_capability_domain_reach_both_neural_stages_and_execution_history():
    import json
    from copy import deepcopy
    from hrc_pilot.joint_world import observable_world
    from hrc_pilot.intent_observation import intent_observation
    from hrc_pilot.tool_joint_human import execution_tool_result
    from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy
    from hrc_pilot.constrained_human_decision import PREFIX
    from test_private_agenda_human import agenda
    r={'time_s':0.,'objects':{'akita_black_bowl_1':[0,0,1.],
        'cream_cheese_1':[.24,0,1.1],'cabinet':[0,-.3,1.]},
        'human_execution':{'held_object':None,'carried_objects':[]},
        'contacts':[],'robot_qpos':[0]*9,'human_body_xy':[.25,.6]}
    regions={name+'_personal':[.2,.4,1.] for name in ['akita_black_bowl_1','cream_cheese_1']}
    scene={'time_s':0.,'objects_xyz':r['objects'],'regions_xyz':regions,
        'movable_object_ids':['akita_black_bowl_1','cream_cheese_1'],
        'own_execution':{'held_object':None,'phase':'idle'},
        'measured_world':observable_world(r,regions,measurement_version=4),
        'public_dialogue':[],'private_context':[],'action_interface':{}}
    proposals=[];contributions=[]
    def propose(payload):
        proposals.append(payload)
        return json.dumps(agenda('Check the actual bowl contents before serving.'))
    def act(payload):
        contributions.append(json.loads(payload))
        return PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
            'contribution':{'kind':'wait'},'communication':None}})+'\n</tool_call>'
    policy=PrivateAgendaHumanPolicy(CONTRACTS['snack_service'].activity,model_path='/unused',
        generator=act,agenda_generator=propose)
    first=policy.decide(scene)
    scene['time_s']=4.;policy.decide(scene)
    request=json.loads(proposals[-1]['messages'][-1]['content'])
    current=json.loads(contributions[-1]['messages'][-1]['content'])
    relation=scene['measured_world']['public_relation_summary']
    assert relation['reference_relations']['akita_black_bowl_1']['observed_supported_items']==[]
    assert request['current_observation']['measured_reference_relations']==relation
    assert current['scene']['measured_reference_relations']==relation
    assert current['human_decision_interface']['movable_object_ids']==scene['movable_object_ids']
    assert request['available_human_contributions']['movable_object_ids']==scene['movable_object_ids']
    feedback=json.loads(next(m['content'] for m in contributions[-1]['messages'] if m['role']=='tool'))
    assert feedback['measured_reference_relations']==relation and first['parse_error'] is None
    legacy=deepcopy(scene);legacy['measured_world']=observable_world(r,regions,measurement_version=3)
    assert 'measured_reference_relations' not in intent_observation(legacy)
    assert 'measured_reference_relations' not in execution_tool_result(0,legacy)
