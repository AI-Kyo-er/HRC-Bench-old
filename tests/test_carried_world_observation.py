from copy import deepcopy

from hrc_pilot.carried_world_observation import observable_carried_world
from hrc_pilot.joint_world import observable_world


def record():
    return {'objects':{'bowl':[0.,0.,1.], 'food':[0.,0.,1.04]},
            'contacts':[{'geom1':'bowl_g1','geom2':'food_g1','distance_m':0.}],
            'robot_qpos':[0.01,-0.01],
            'human_execution':{'held_object':'bowl','carried_objects':['bowl','food']}}


def regions():
    return {'bowl_personal':[0.,0.,.9],'food_personal':[.2,0.,.9]}


def test_carried_payload_keeps_contact_but_cannot_be_reported_as_released():
    current=record();before=deepcopy(current)
    old=observable_world(current,regions(),measurement_version=4)
    result=observable_carried_world(current,regions())
    assert old['released_object_support_contacts']['food']==['bowl']
    assert result['released_object_support_contacts']['food']==[]
    assert result['public_scene_measurements']['objects']['food']['human_carried']
    assert result['object_contacts']['food']['contact_entities']==['bowl']
    assert not any(x.startswith('food is released') for x in result['current_measured_fact_sentences'])
    assert result['public_relation_summary']==old['public_relation_summary']
    assert current==before


def test_release_restores_supported_food_and_legacy_measurement_is_unchanged():
    current=record();current['human_execution']={'held_object':None,'carried_objects':[]}
    legacy=observable_world(current,regions(),measurement_version=4)
    result=observable_carried_world(current,regions())
    assert result['released_object_support_contacts']['food']==['bowl']
    assert result['public_scene_measurements']['objects']['food']['released_from_hands']
    result['measurement_version']=4
    assert result==legacy


def test_robot_contact_still_prevents_released_claim_after_human_release():
    current=record();current['human_execution']={'held_object':None,'carried_objects':[]}
    current['contacts'].append({'geom1':'food_g1','geom2':'gripper0_finger_pad','distance_m':0.})
    result=observable_carried_world(current,regions())
    assert result['released_object_support_contacts']['food']==[]
    assert not result['public_scene_measurements']['objects']['food']['released_from_hands']
