from hrc_pilot.native_placement import NativePlacementEvidence


def record(time, *, held=False, aperture=.08, supported=True, x=0.):
    contacts=[]
    if supported:contacts.append({'geom1':'bowl_g0','geom2':'plate_g0'})
    if held:contacts.append({'geom1':'gripper0_finger1','geom2':'bowl_g1'})
    return {'time_s':time,'objects':{'bowl':[x,0,.9],'plate':[0,0,.89]},
            'robot_qpos':[aperture/2,-aperture/2],'contacts':contacts}


def test_geometry_and_support_while_grasping_cannot_complete_placement():
    score=NativePlacementEvidence('bowl','plate')
    for i in range(1,11):assert not score.update(record((i-1)*.05,held=True),record(i*.05,held=True),True)
    assert score.duration==0 and score.records[-1]['gripper_contact']


def test_release_requires_support_and_stability_then_accumulates_actual_time():
    score=NativePlacementEvidence('bowl','plate')
    assert not score.update(record(0),record(.05,supported=False),True)
    assert not score.update(record(.05),record(.10,x=.1),True)
    for i in range(3,6):assert not score.update(record((i-1)*.05),record(i*.05),True)
    assert score.update(record(.25),record(.30),True)


def test_closed_gripper_without_collision_is_not_evidence_of_release():
    score=NativePlacementEvidence('bowl','plate')
    assert not score.update(record(0,aperture=.008),record(.2,aperture=.008),True)
