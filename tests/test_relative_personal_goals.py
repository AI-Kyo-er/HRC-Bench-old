from types import SimpleNamespace
import pytest

from hrc_pilot.native_autonomous_human import validate_targets
from hrc_pilot.native_personal_evidence import evaluate_personal_goals,signature
from hrc_pilot.continual_activity_metrics import evaluate_continual_activity


def test_relative_goal_is_available_only_in_declared_tool_interface():
    obs=SimpleNamespace(objects={'food':(0,0,1),'plate':(0,0,.9)},regions={})
    targets=[['food','on:plate']]
    assert validate_targets(targets,obs,allow_pair_arrays=True)[1]
    chosen,error=validate_targets(targets,obs,allow_pair_arrays=True,relative_destinations=['on:plate'])
    assert error is None and chosen==[{'object_id':'food','destination':'on:plate'}]
    assert validate_targets([['food','on:food']],obs,allow_pair_arrays=True,relative_destinations=['on:food'])[1]


def test_relative_goal_follows_receiver_and_requires_contact_and_both_hand_release():
    trace=[]
    for i in range(12):
        x=0. if i<6 else .2
        contacts=[{'geom1':'food_g1','geom2':'plate_g1'}]
        if i==7:contacts.append({'geom1':'food_g1','geom2':'human_palm_contact'})
        trace.append({'time_s':i*.05,'physics_time_s':i*.05,'objects':{'food':[x,0.,1.],'plate':[x,0.,.9]},'contacts':contacts})
    decision={'time_s':0.,'personal_goal_state':{'personal_targets':[{'object_id':'food','destination':'on:plate'}],'long_term_intention':'在餐盘上保留食物','target_validation_error':None},'negotiation_proposal_messages':[]}
    placements=[{'time_s':i*.05,'released_stable_placement':True} for i in range(1,12)]
    with pytest.raises(ValueError):evaluate_personal_goals({},trace,[],[decision],placements)
    personal=evaluate_personal_goals({},trace,[],[decision],placements,allow_relative_relations=True)
    assert personal['human_current_observable_goals_satisfied']
    continual=evaluate_continual_activity(trace,[decision],{},placements)
    assert continual['semantic_target_set_changes']==0 and continual['final_joint_released_stable']
    assert not continual['records'][6]['human_released_stable_goals']
    assert signature([{'object_id':'food','destination':'on:plate'}],{})==(('food','on:plate'),)
