import json
from hrc_pilot.contribution_joint_human import ContributionJointHumanPolicy
from hrc_pilot.joint_activity import ACTIVITIES


def test_actual_neural_input_explains_parameter_domain_and_null_speech_preserves_intent():
    inputs=[]
    def generate(prompt):
        inputs.append(json.loads(prompt))
        return '{"action":"relocate","object_id":"wine","destination":"drink_staging","message":null,"message_kind":null,"memory":null,"intention":"Provide bottle for storage."}'
    policy=ContributionJointHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate,reflection=True)
    scene={'time_s':0,'objects_xyz':{'wine':[0,0,1]},'regions_xyz':{'drink_staging':[0,0,1]},
        'own_execution':{'held_object':'wine','phase':'idle','last_receipt':None},
        'measured_world':{'current_measured_fact_sentences':['Human is holding wine.']},
        'public_dialogue':[],'private_context':[],'action_interface':{'relocate_can_buffer_owned_object':True}}
    row=policy.decide(scene)
    assert row['choice']['action']=='relocate' and row['choice']['intention']=='Provide bottle for storage.'
    assert row['parse_error'] is None and row['choice']['message']==''
    assert row['private_input']==inputs[0] and row['reflection_input']==inputs[1]
    assert inputs[0]['human_contribution_interface']['destination_choices'][0]['destination_id']=='drink_staging'
    assert row['choice_schema_version']==4 and row['neural_inferences']==2
