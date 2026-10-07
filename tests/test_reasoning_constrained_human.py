import json

from hrc_pilot.reasoning_constrained_human import ReasoningConstrainedHumanPolicy,reasoning_request
from hrc_pilot.constrained_human_decision import PREFIX
from hrc_pilot.joint_activity import ACTIVITIES


def test_capability_documents_do_not_become_partner_requests_and_actual_choice_is_preserved():
    inputs=[]
    raw=PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
        'contribution':None,'communication':{'kind':'request','text':'Do you need this bottle stored on the rack?'},
        'intention':'Clarify the actual arrangement before acting.'}})+'\n</tool_call>'
    def generate(payload):inputs.append(json.loads(payload));return raw
    human=ReasoningConstrainedHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate)
    scene={'time_s':0.,'objects_xyz':{'wine':[]},'regions_xyz':{'staging':[]},
        'own_execution':{'held_object':'wine','phase':'idle'},'measured_world':{},'private_context':[],
        'public_dialogue':[{'speaker':'environment','text':'Possible tool: put bottle on cabinet.'},
                           {'speaker':'robot','text':'Please prepare the bottle.'}],
        'action_interface':{}}
    row=human.decide(scene)
    actual=json.loads(inputs[0]['messages'][-1]['content'])
    assert actual==row['private_input']
    assert actual['scene']['public_partner_statements_not_execution_facts']==[scene['public_dialogue'][1]]
    assert row['choice_schema_version']==10 and row['parse_error'] is None
    assert row['choice']['message']=='Do you need this bottle stored on the rack?'
    assert row['generation_thinking'] is True
