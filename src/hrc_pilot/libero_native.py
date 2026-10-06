"""原生LIBERO输入与物理证据；不经过Genesis坐标映射或语义动作执行器。"""
from hashlib import sha256

import numpy as np


def native_policy_input(observation, instruction):
    quaternion = np.asarray(observation['robot0_eef_quat'], dtype=np.float64)
    w = np.clip(quaternion[3], -1., 1.)
    denominator = np.sqrt(max(0., 1 - w * w))
    rotation = np.zeros(3) if denominator < 1e-10 else quaternion[:3] * (2 * np.arccos(w) / denominator)
    state = np.r_[observation['robot0_eef_pos'], rotation, observation['robot0_gripper_qpos']].astype(np.float32)
    if state.shape != (8,) or not np.isfinite(state).all():
        raise ValueError('需要原生末端位置、轴角及有符号双指状态')
    # Same convention as upstream OpenPI LIBERO evaluation / LeRobot env processor.
    return {'observation/image': np.ascontiguousarray(observation['agentview_image'][::-1, ::-1]),
            'observation/wrist_image': np.ascontiguousarray(observation['robot0_eye_in_hand_image'][::-1, ::-1]),
            'observation/state': state, 'prompt': instruction}


def input_audit(request):
    return {'model_input_keys': list(request), 'prompt': request['prompt'],
            'state': request['observation/state'].tolist(),
            'exterior_rgb_sha256': sha256(request['observation/image'].tobytes()).hexdigest(),
            'wrist_rgb_sha256': sha256(request['observation/wrist_image'].tobytes()).hexdigest(),
            'image_orientation': 'rotate_180_from_raw_simulator'}


def physical_record(env, observation, *, time_s, step):
    sim = env.sim
    objects = {name: sim.data.body_xpos[body].tolist() for name, body in env.env.obj_body_id.items()}
    contacts = []
    for index in range(sim.data.ncon):
        contact = sim.data.contact[index]
        contacts.append({'geom1': sim.model.geom_id2name(contact.geom1),
                         'geom2': sim.model.geom_id2name(contact.geom2),
                         'distance_m': float(contact.dist)})
    from .native_goal_evidence import fixture_joint_measurements
    return {'articulated_joints':fixture_joint_measurements(env), 'time_s': time_s, 'step': step, 'physics_time_s': float(sim.data.time),
            'objects': objects, 'robot_qpos': np.r_[observation['robot0_joint_pos'],
                                                  observation['robot0_gripper_qpos']].tolist(),
            'robot_ee': observation['robot0_eef_pos'].tolist(),
            'eef_quaternion_xyzw': observation['robot0_eef_quat'].tolist(),
            'qpos': sim.data.qpos.tolist(), 'qvel': sim.data.qvel.tolist(),
            'ctrl': sim.data.ctrl.tolist(), 'contacts': contacts}


def perceived_object_contacts(record):
    """理想模拟感知的实际接触实体；不读取完成谓词或评分。"""
    result={name:{'contact_entities':[],'robot_hand_contact':False,'human_hand_contact':False} for name in record['objects']}
    for pair in record['contacts']:
        a,b=pair['geom1'] or '',pair['geom2'] or ''
        for name in result:
            other=b if a.startswith(name+'_') else a if b.startswith(name+'_') else None
            if other is None:continue
            if other.startswith('gripper'):result[name]['robot_hand_contact']=True
            if other.startswith(('human_left_finger','human_right_finger','human_palm','human_fingertip')):result[name]['human_hand_contact']=True
            entity=next((n for n in result if other.startswith(n+'_')),None)
            if other=='table_collision':entity='table'
            if entity and entity not in result[name]['contact_entities']:result[name]['contact_entities'].append(entity)
    for value in result.values():value['contact_entities'].sort()
    return result
