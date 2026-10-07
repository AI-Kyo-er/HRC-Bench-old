from hrc_pilot.native_contact_observation import own_contact_observation


def test_own_peer_contact_does_not_depend_on_target_object_or_task_score():
    rows=[{'geom1':'human_palm_contact','geom2':'robot0_link7_collision','distance_m':-.0001},
          {'geom1':'plate_g1','geom2':'human_left_finger_contact','distance_m':-.001},
          {'geom1':'human_right_finger_contact','geom2':'table_collision','distance_m':.002}]
    human=own_contact_observation(rows,'human');robot=own_contact_observation(rows,'robot')
    assert human['contact_geoms']==['plate_g1','robot0_link7_collision']
    assert human['contact_with_other_agent'] and robot['contact_with_other_agent']
    assert robot['contact_geoms']==['human_palm_contact']
    assert 'goal_success' not in human and 'recommended_action' not in human
