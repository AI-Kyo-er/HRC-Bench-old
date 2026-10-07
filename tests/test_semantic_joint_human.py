import json
from hrc_pilot.semantic_joint_human import SemanticJointHumanPolicy
from hrc_pilot.joint_activity import ACTIVITIES


def test_logged_private_input_is_the_actual_compact_neural_input_with_original_scene_separate():
    inputs=[]
    def generate(prompt):
        inputs.append(json.loads(prompt))
        return '{"action":"message","message":"Please check the drawer; it is not accessible.","message_kind":"request","memory":"Observed closed drawer."}'
    policy=SemanticJointHumanPolicy(ACTIVITIES['drawer_access'],model_path='/unused',generator=generate,reflection=True)
    scene={'time_s':4,'objects_xyz':{'cream_cheese_1':[.1,.2,1.]},'regions_xyz':{'drawer_storage':[0,0,1]},
        'own_execution':{'held_object':'plate_1','phase':'idle','last_receipt':{'error':'destination_not_physically_accessible','accepted':False}},
        'measured_world':{'current_measured_fact_sentences':['Drawer is closed.'],'drawer':{'placement_accessible':False}},
        'public_dialogue':[{'speaker':'robot','text':'Drawer opened.'}],'private_context':[],
        'action_interface':{'actions':['relocate','message','wait']},'score':True}
    row=policy.decide(scene)
    assert row['private_input']==inputs[0] and row['reflection_input']==inputs[1]
    assert row['observation_source_scene']==scene
    assert inputs[0]['scene']['measured_current_facts']==['Drawer is closed.']
    assert inputs[0]['scene']['public_partner_statements_not_execution_facts'][0]['text']=='Drawer opened.'
    assert not {'score','objects_xyz','regions_xyz'}.intersection(inputs[0]['scene'])
    assert row['parse_error'] is None and row['choice']['message_kind']=='request'
    assert row['neural_inferences']==2


def test_auxiliary_kind_does_not_discard_a_valid_public_correction():
    from hrc_pilot.semantic_joint_human import parse_semantic_choice
    raw='{"action":"message","message_kind":"feedback","message":"The drawer is still closed."}'
    choice=parse_semantic_choice(raw,{}, {})
    assert choice['message']=='The drawer is still closed.' and choice['message_kind']=='notice'
    assert choice['declared_message_kind']=='feedback'
