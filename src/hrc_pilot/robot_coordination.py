"""视觉协调器的公共请求、命令校验与保持姿态原语，不包含任务路由。"""
import base64
from hashlib import sha256
from io import BytesIO
import json

import numpy as np
from PIL import Image
from .native_contact_observation import own_contact_observation


PUBLIC_KEYS={'time_s','robot_task','human_task','dialogue','state','images','history','current_goal','self_execution'}


def image_payload(pixels):
    rgb=np.asarray(pixels)
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8:raise ValueError('需要真实RGB uint8相机帧')
    buffer=BytesIO();Image.fromarray(rgb).save(buffer,format='PNG')
    return {'png_base64':base64.b64encode(buffer.getvalue()).decode(),
            'rgb_sha256':sha256(rgb.tobytes()).hexdigest()}


def decode_image(payload):
    image=Image.open(BytesIO(base64.b64decode(payload['png_base64']))).convert('RGB')
    assert sha256(np.asarray(image).tobytes()).hexdigest()==payload['rgb_sha256']
    return image


def coordination_request(*, time_s, robot_task, human_task, dialogue, state, images, history, current_goal, self_execution):
    state=np.asarray(state,dtype=float)
    if state.shape!=(8,) or not np.isfinite(state).all():raise ValueError('需要机械臂自身8维状态')
    return {'time_s':float(time_s),'robot_task':robot_task,'human_task':human_task,
            'dialogue':[{'speaker':m.speaker,'kind':m.kind,'text':m.text} for m in dialogue[-20:]],
            'state':state.tolist(),'images':{key:image_payload(value) for key,value in images.items()},
            'history':history[-6:],'current_goal':current_goal,'self_execution':self_execution}


def execution_feedback(record, initial_state, calls, actions):
    state=np.asarray(record['robot_qpos'],dtype=float)
    fingers={name:0 for name in ['finger_1','finger_2']}
    for c in record['contacts']:
        for geom in [c['geom1'] or '',c['geom2'] or '']:
            if geom.startswith('gripper0_finger1'):fingers['finger_1']+=1
            if geom.startswith('gripper0_finger2'):fingers['finger_2']+=1
    return {'source':'actual_native_controls_and_own_sensors',
            'own_contact_report':own_contact_observation(record['contacts'],'robot'),
            'completed_native_control_steps':len(actions),
            'issued_learned_vla_blocks':sum(c['action_source']=='learned_vla' for c in calls),
            'issued_hold_blocks':sum(c['action_source'] in {'vlm_selected_hold_primitive','planner_output_rejection_hold_primitive'} for c in calls),
            'issued_cartesian_blocks':sum(c['action_source']=='vlm_selected_cartesian_primitive' for c in calls),
            'last_cartesian_target_xyz_m':calls[-1].get('cartesian_target_xyz_m') if calls else None,
            'last_control_source':calls[-1]['action_source'] if calls else 'no_control_yet',
            'last_native_action':actions[-1]['action'] if actions else None,
            'eef_xyz_m':record['robot_ee'],
            'eef_displacement_from_start_m':float(np.linalg.norm(np.asarray(record['robot_ee'])-np.asarray(initial_state)[:3])),
            'signed_finger_joint_positions_m':state[-2:].tolist(),
            'measured_gripper_aperture_m':float(np.abs(state[-2:]).sum()),
            'finger_contact_sample_counts':fingers,
            'interpretation':'已发生的动作和自身传感器测量，不是意图、不认定抓取成功或任务完成。'}


def validate_decision(raw):
    error=None
    try:
        value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        if not isinstance(value,dict) or value.get('mode') not in {'execute','hold','move_ee'}:raise ValueError('mode必须为execute、hold或move_ee')
        if value['mode']=='execute' and (not isinstance(value.get('instruction'),str) or not value['instruction'].strip()):raise ValueError('execute必须给出运动目标指令')
        if value['mode']=='move_ee':
            delta=np.asarray(value.get('delta_xyz_m'),dtype=float)
            if delta.shape!=(3,) or not np.isfinite(delta).all() or np.linalg.norm(delta)>.2+1e-9:
                raise ValueError('move_ee须给出有限3维delta_xyz_m，向量长度最多0.2米')
    except (ValueError,TypeError) as exc:
        error=str(exc);value={'mode':'hold','reason':'输出无效，维持当前姿态。'}
    decision={key:str(value.get(key,''))[:500] for key in ['mode','instruction','message','reason','memory_note','current_goal']}
    decision['message']=decision['message'][:240]
    decision['plan']=[str(v)[:180] for v in value.get('plan',[])[:5]] if isinstance(value.get('plan',[]),list) else []
    if decision['mode']=='move_ee':decision['delta_xyz_m']=delta.tolist()
    return decision,error


def hold_actions(state, steps, last_gripper_action=None):
    """执行模型选择的保持姿态；根据自身夹爪开度维持开/闭，不选协作策略。"""
    state=np.asarray(state,dtype=float)
    actions=np.zeros((steps,7),dtype=float)
    actions[:,-1]=(float(last_gripper_action) if last_gripper_action is not None
                  else (-1. if np.abs(state[-2:]).sum()>=.04 else 1.))
    return actions


def cartesian_actions(state,target,steps,last_gripper_action=None):
    """将模型选择的目标转换为原生OSC增量；每动作块重新读取实际末端位置。

    原生OSC xyz缩放0.05m，20Hz，参考速度最多0.05m/s。
    不选择目标、不检查任务成绩、不修改物体或机器人位姿。
    """
    state=np.asarray(state,dtype=float);target=np.asarray(target,dtype=float)
    if state.shape!=(8,) or target.shape!=(3,) or not np.isfinite(np.r_[state,target]).all():
        raise ValueError('末端状态与目标须为有限坐标')
    actions=hold_actions(state,steps,last_gripper_action)
    reference=state[:3].copy()
    for index in range(steps):
        error=target-reference;distance=np.linalg.norm(error)
        increment=error*min(1.,.0025/max(distance,1e-12))
        actions[index,:3]=increment/.05;reference+=increment
    return actions


class CoordinatorClient:
    def __init__(self, port):
        import requests
        self.session=requests.Session();self.session.trust_env=False
        self.url=f'http://127.0.0.1:{port}'
        response=self.session.get(self.url+'/metadata',timeout=10);response.raise_for_status()
        self.metadata=response.json()

    def infer(self, request):
        if set(request)!=PUBLIC_KEYS:raise ValueError('协调器只能读取公开请求字段')
        response=self.session.post(self.url+'/infer',json=request,timeout=180);response.raise_for_status()
        return response.json()
