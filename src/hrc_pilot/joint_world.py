"""由当前几何／接触构建共同活动测量；不读取目标成绩、不选择动作。"""
import numpy as np

from .libero_native import perceived_object_contacts


def drawer_support(env):
    model,data=env.sim.model,env.sim.data
    name='wooden_cabinet_1_g27';joint='wooden_cabinet_1_middle_level'
    geom=model.geom_name2id(name)
    axes=data.geom_xmat[geom].reshape(3,3);center=data.geom_xpos[geom].copy()
    top=center[2]+float(np.dot(np.abs(axes[2]),model.geom_size[geom]))
    opening=-float(data.get_joint_qpos(joint))
    return {'support_xyz':[float(center[0]),float(center[1]),top],
            'opening_m':opening,'geometry_source':name,'joint_source':joint,
            'placement_accessible':opening>=.10}


def update_joint_regions(env,regions):
    if 'drawer_storage' not in regions:return None
    support=drawer_support(env)
    cream='cream_cheese_1';obj=env.env.objects_dict[cream]
    offset=float(-obj.bottom_offset[2])
    regions['drawer_storage']=tuple(np.asarray(support['support_xyz'])+[0,0,offset+.002])
    env.env._hrc_region_accessibility={'drawer_storage':support['placement_accessible']}
    try:
        marker=env.sim.model.geom_name2id('human_public_region_drawer_storage')
        env.sim.model.geom_pos[marker]=np.asarray(support['support_xyz'])+[0,0,.0008]
    except ValueError:pass
    return support


def observable_world(record,regions,drawer=None,*,measurement_version=2):
    if measurement_version not in {1,2,3}:raise ValueError('未知共同环境测量版本')
    contacts=perceived_object_contacts(record)
    distances={name:{region:round(float(np.linalg.norm(np.asarray(xyz)[:2]-np.asarray(point)[:2])),4)
                     for region,point in regions.items() if region.endswith(('ready','staging','storage','delivery'))}
               for name,xyz in record['objects'].items()}
    relative={}
    if 'akita_black_bowl_1' in record['objects'] and 'cream_cheese_1' in record['objects']:
        delta=np.asarray(record['objects']['cream_cheese_1'])-record['objects']['akita_black_bowl_1']
        relative['cream_cheese_1_to_akita_black_bowl_1']={'xy_distance_m':float(np.linalg.norm(delta[:2])),
                                                      'relative_height_m':float(delta[2])}
    supported={}
    for name,info in contacts.items():
        if info['robot_hand_contact'] or record.get('human_execution',{}).get('held_object')==name:
            supported[name]=[];continue
        supported[name]=[entity for entity in info['contact_entities']
            if entity=='table' or (entity in record['objects']
                and record['objects'][name][2]>=record['objects'][entity][2]
                and np.linalg.norm(np.asarray(record['objects'][name])[:2]-np.asarray(record['objects'][entity])[:2])<.03)]
        # 柜体中心不是抽屉底面的位置。真实底面接触才构成此处的支撑事实；
        # 只有XY接近、侧壁接触或尚在手中，不能称已收纳或已完成共同活动。
        if measurement_version>=2 and drawer and drawer.get('geometry_source'):
            xyz=np.asarray(record['objects'][name]);surface=np.asarray(drawer['support_xyz'])
            bottom=drawer['geometry_source']
            bottom_contact=any(bottom in (pair['geom1'],pair['geom2']) and
                any((g or '').startswith(name+'_') for g in (pair['geom1'],pair['geom2']))
                for pair in record['contacts'])
            if bottom_contact and np.linalg.norm(xyz[:2]-surface[:2])<.03 and 0<=xyz[2]-surface[2]<.05:
                supported[name].append('middle_drawer_bottom')
    near_regions={name:[region for region,distance in ds.items() if distance<.025]
                  for name,ds in distances.items()}
    facts=[]
    for name in record['objects']:
        if supported[name]:facts.append(f'{name} is released and has support contact with '+', '.join(supported[name])+'.')
        if contacts[name]['robot_hand_contact']:facts.append(f'Robot fingers currently contact {name}; contact alone is not completion.')
        if near_regions[name]:facts.append(f'{name} is within 25mm XY of '+', '.join(near_regions[name])+'.')
    held=record.get('human_execution',{}).get('held_object')
    facts.append(f'Human is holding {held}.' if held else 'Human is not holding any object.')
    if 'human_body_xy' in record:facts.append('Human body is '+('aside from the workspace.' if record['human_body_xy'][1]>=.8 else 'near the workspace.'))
    if drawer:facts.append(f'Middle drawer opening is {drawer["opening_m"]:.3f}m; interior placement is '+('accessible.' if drawer['placement_accessible'] else 'not accessible.'))
    world={'source':'current_geometry_and_contact_measurement_not_task_score',
        'object_contacts':contacts,'object_distance_to_named_region_xy_m':distances,
        'released_object_support_contacts':supported,'near_named_regions':near_regions,
        'current_measured_fact_sentences':facts,
        'relative_object_positions':relative,'drawer':drawer,
        'robot_gripper_aperture_m':float(np.abs(np.asarray(record['robot_qpos'])[-2:]).sum())}
    if measurement_version>=2:world['measurement_version']=measurement_version
    if measurement_version>=3:
        from .public_scene_measurements import public_scene_measurements
        movable=[name for name in record['objects'] if name+'_personal' in regions]
        world['public_scene_measurements']=public_scene_measurements(record,movable)
    return world


def actual_robot_execution(record,calls,controls):
    contact=perceived_object_contacts(record)
    return {'source':'own_recorded_actions_and_current_sensors_not_generated_history',
        'actual_vla_blocks':sum(c['action_source'] in {'actual_vla_public_dialogue','actual_vla_coordinator_instruction'} for c in calls),
        'actual_hold_blocks':sum(c['action_source']=='coordinator_selected_hold' for c in calls),
        'actual_cartesian_blocks':sum(c['action_source']=='coordinator_selected_cartesian_control' for c in calls),
        'actual_control_steps':len(controls),'last_action':controls[-1]['action'] if controls else None,
        'eef_xyz':record['robot_ee'],'gripper_aperture_m':float(np.abs(np.asarray(record['robot_qpos'])[-2:]).sum()),
        'gripper_contact_objects':[name for name,v in contact.items() if v['robot_hand_contact']],
        'last_action_source':calls[-1]['action_source'] if calls else 'no_action_issued'}
