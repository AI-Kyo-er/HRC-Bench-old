from hrc_pilot.continual_activity_metrics import evaluate_continual_activity


def test_empty_goals_are_unevaluable_and_alias_changes_do_not_count_as_new_intention():
    trace=[{'time_s':i*.05,'objects':{'plate':[0.,0.,.9]},'contacts':[{'geom1':'plate_g1','geom2':'table_collision'}]} for i in range(11)]
    def decision(t,targets):return {'time_s':t,'personal_goal_state':{'personal_targets':targets}}
    goals=[decision(0,[]),decision(.1,[{'object_id':'plate','destination':'home'}]),decision(.3,[{'object_id':'plate','destination':'alias'}])]
    placements=[{'time_s':i*.05,'released_stable_placement':True} for i in range(1,11)]
    value=evaluate_continual_activity(trace,goals,{'home':(0.,0.,.9),'alias':(0.,0.,.9)},placements)
    assert abs(value['human_goal_unevaluable_time_s']-.1)<1e-9
    assert value['semantic_target_set_changes']==1 and value['new_relations_from_episode_start_count']==0
    assert abs(value['first_joint_released_stable_s']-.3)<1e-9 and value['final_joint_released_stable']


def test_human_palm_contact_excludes_success_even_if_coordinates_and_robot_goal_hold():
    trace=[{'time_s':i*.05,'objects':{'plate':[0.,0.,.9]},'contacts':[
        {'geom1':'plate_g1','geom2':'table_collision'},{'geom1':'plate_g1','geom2':'human_palm_contact'}]} for i in range(6)]
    decisions=[{'time_s':0,'personal_goal_state':{'personal_targets':[{'object_id':'plate','destination':'home'}]}}]
    placements=[{'time_s':i*.05,'released_stable_placement':True} for i in range(1,6)]
    value=evaluate_continual_activity(trace,decisions,{'home':(0.,0.,.9)},placements)
    assert value['joint_released_goal_time_s']==0. and not value['final_joint_released_stable']
