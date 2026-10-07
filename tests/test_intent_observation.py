from copy import deepcopy
from hrc_pilot.intent_observation import intent_observation


def test_partner_claim_is_not_promoted_to_world_fact_and_rejection_remains_visible():
    scene={'time_s':12,'objects_xyz':{'cream':[0,0,1]},'regions_xyz':{'drawer':[0,0,1]},
        'own_execution':{'held_object':'plate','phase':'idle','completed_requests':[],
                         'last_receipt':{'accepted':False,'error':'destination_not_physically_accessible'}},
        'measured_world':{'current_measured_fact_sentences':['Middle drawer is not accessible.'],
                         'drawer':{'opening_m':0.,'placement_accessible':False}},
        'public_dialogue':[{'speaker':'robot','text':'Drawer is open.'}],
        'private_context':[{'time_s':10,'text':'Need to leave soon.'}],'action_interface':{'actions':['relocate','wait']},
        'score':True,'robot_motion':{'eef_speed_m_s':0.}}
    original=deepcopy(scene);obs=intent_observation(scene)
    assert scene==original and obs['drawer_measurement']['placement_accessible'] is False
    assert obs['measured_current_facts']==['Middle drawer is not accessible.']
    assert obs['public_partner_statements_not_execution_facts'][0]['text']=='Drawer is open.'
    assert obs['own_execution']['last_rejection_fact']=='The requested destination is not physically accessible now.'
    assert not {'score','task_success','objects_xyz','regions_xyz','robot_qpos'}.intersection(obs)
    assert obs['object_ids']==['cream'] and obs['named_destinations']==['drawer']
    assert obs['private_context']==scene['private_context']
