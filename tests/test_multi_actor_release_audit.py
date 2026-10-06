import json

from scripts.audit_multi_actor_release import audit


def test_unrelated_closed_gripper_does_not_override_actual_support_and_release(tmp_path):
    def state(t,hand):
        contacts=[{'geom1':'food_g0','geom2':'bowl_g0'}]
        if hand:contacts.append({'geom1':'food_g0','geom2':hand})
        return {'time_s':t,'objects':{'food':[0.,0.,1.],'bowl':[0.,0.,.99]},'contacts':contacts}
    (tmp_path/'metrics.json').write_text(json.dumps({'robot_goal_spec':{'kind':'on','object_id':'food','receiver_id':'bowl'}}))
    def run(hand):
        (tmp_path/'trace.jsonl').write_text('\n'.join(json.dumps(state(t,hand)) for t in [0.,.1,.2]))
        (tmp_path/'placement_evidence.jsonl').write_text('\n'.join(json.dumps({'time_s':t,'native_geometry_satisfied':True,'released_stable_placement':False}) for t in [.1,.2]))
        return audit(tmp_path)
    result=run(None)
    assert result['final_all_actor_released_stable'] and result['first_all_actor_released_stable_s']==.2
    assert not result['raw_final_aperture_dependent_success']
    for hand in ['human_palm_contact','human_left_finger_contact','gripper0_finger']:
        assert not run(hand)['final_all_actor_released_stable']
