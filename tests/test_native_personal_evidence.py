from hrc_pilot.native_personal_evidence import evaluate_personal_goals


def records():
    return [{'time_s':i*.05,'physics_time_s':i*.05,'objects':{'cookies_1':[0,0,.9]}} for i in range(21)]


def decision(time,intention,targets):
    return {'time_s':time,'personal_goal_state':{'personal_targets':targets,'long_term_intention':intention,'target_validation_error':None},'negotiation_proposal_messages':[]}


def test_intention_paraphrase_and_region_alias_do_not_count_as_observable_goal_change():
    ds=[decision(0,'准备点心',[{'object_id':'cookies_1','destination':'a'}]),
        decision(.5,'我要准备好点心',[{'object_id':'cookies_1','destination':'alias'}])]
    r=evaluate_personal_goals({'a':(0,0,.9),'alias':(0,0,.9)},records(),[],ds,[])
    assert r['observable_target_set_changes']==0
    assert r['new_target_intervals_with_stable_relation']==0
    assert r['human_current_observable_goals_satisfied']


def test_empty_subjective_intention_is_not_scored_as_fulfilled_object_goal():
    r=evaluate_personal_goals({},records(),[],[decision(0,'休息',[])],[])
    assert not r['human_current_observable_goals_evaluable']
    assert not r['joint_observable_goals_satisfied']


def test_shelf_position_while_still_gripped_is_not_released_placement():
    ds=[decision(0,'放到高台',[{'object_id':'cookies_1','destination':'cookies_shelf'}])]
    trace=records()
    for r in trace:r['contacts']=[{'geom1':'cookies_1_box','geom2':'human_left_finger_contact'},{'geom1':'cookies_1_box','geom2':'human_storage_support'}]
    old=evaluate_personal_goals({'cookies_shelf':(0,0,.9)},trace,[],ds,[])
    actual=evaluate_personal_goals({'cookies_shelf':(0,0,.9)},trace,[],ds,[],require_shelf_release=True)
    assert old['human_current_observable_goals_satisfied']
    assert not actual['human_current_observable_goals_satisfied']
    for r in trace:r['contacts']=r['contacts'][1:]
    assert evaluate_personal_goals({'cookies_shelf':(0,0,.9)},trace,[],ds,[],require_shelf_release=True)['human_current_observable_goals_satisfied']
