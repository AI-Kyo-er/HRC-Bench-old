from copy import deepcopy

from hrc_pilot.joint_process_metrics import original_arrangement_observations


def test_empty_bowl_or_held_delivery_is_not_a_released_filled_snack_witness():
    r={'time_s':0.,'objects':{'akita_black_bowl_1':[.2,.3,1],'cream_cheese_1':[.2,.3,1.04]},
       'human_execution':{'held_object':None},'contacts':[{'geom1':'akita_black_bowl_1_g1','geom2':'table_collision'}]}
    trace=[r,{**deepcopy(r),'time_s':1.},{**deepcopy(r),'time_s':2.}]
    placements=[{'time_s':1.,'released_stable_placement':False},{'time_s':2.,'released_stable_placement':False}]
    regions={'snack_delivery':[.2,.3,1]}
    obs=original_arrangement_observations('snack_service',trace,placements,regions)
    assert obs['terminal_observation']['original_spatial_criterion']
    assert not obs['terminal_observation']['physical_match'] and obs['first_physical_match_s'] is None
    for p in placements:p['released_stable_placement']=True
    trace[-1]['human_execution']['held_object']='akita_black_bowl_1'
    obs=original_arrangement_observations('snack_service',trace,placements,regions)
    assert obs['first_physical_match_s']==1. and not obs['last_second_consistently_matches']
    trace[-1]['human_execution']['held_object']=None
    obs=original_arrangement_observations('snack_service',trace,placements,regions)
    assert obs['last_second_consistently_matches'] and obs['current_arrangement_score'] is None
    trace[-1]['human_execution']['held_object']='cream_cheese_1'
    obs=original_arrangement_observations('snack_service',trace,placements,regions)
    assert obs['terminal_observation']['released_primary']
    assert not obs['terminal_observation']['physical_match']


def test_original_rack_failure_is_not_a_failure_score_for_an_updated_arrangement():
    r={'time_s':0.,'objects':{'wine_bottle_1':[.2,.3,1]},'human_execution':{'held_object':None},
       'contacts':[{'geom1':'wine_bottle_1_g1','geom2':'table_collision'}]}
    result=original_arrangement_observations('drink_storage',[r,{**deepcopy(r),'time_s':1.}],
        [{'time_s':1.,'released_stable_placement':False}],{})
    assert not result['terminal_observation']['physical_match']
    assert result['current_arrangement_score'] is None
