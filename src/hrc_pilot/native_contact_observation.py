"""主体自己的几何接触感知；不提供任务成绩、意图或接触力估计。"""


HAND_PREFIXES=('human_fingertip','human_palm','human_left_finger','human_right_finger')


def own_contact_observation(contacts,role):
    prefixes=HAND_PREFIXES if role=='human' else ('robot','gripper')
    observed=[]
    for pair in contacts:
        a,b=pair['geom1'] or '',pair['geom2'] or ''
        if not a.startswith(prefixes) and b.startswith(prefixes):a,b=b,a
        if a.startswith(prefixes) and not b.startswith(prefixes) and pair['distance_m']<=0:
            observed.append({'own_geom':a,'other_geom':b,'distance_m':pair['distance_m']})
    peers=sorted({p['other_geom'] for p in observed})
    return {'source':'current_collision_geometry_no_force_or_goal_inference','contact_geoms':peers,
            'contacts':observed,'contact_with_other_agent':any(n.startswith(('robot','gripper') if role=='human' else HAND_PREFIXES) for n in peers)}
