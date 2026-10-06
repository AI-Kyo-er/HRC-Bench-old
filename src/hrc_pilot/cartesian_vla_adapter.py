"""LIBERO末端动作到实际机器人关节控制；不查询任务对象几何。"""
from hashlib import sha256
from time import perf_counter

import numpy as np
from scipy.spatial.transform import Rotation

from .protocol import Action
from .robot_control import hand_rotation


class CartesianVLAAdapter:
    continuous_control = True

    def __init__(self, infer, robot, *, instruction, execution_horizon=5,
                 policy_translation=(-0.56, 0.0, 0.0), tcp_offset=(0,0,0.1034)):
        self.infer, self.robot = infer, robot
        self.instruction, self.execution_horizon = instruction, execution_horizon
        self.translation = np.array(policy_translation)
        self.tcp_offset = np.array(tcp_offset)
        self.reset()

    def reset(self):
        self.chunk=[]
        self.cursor=0
        self.calls=0
        self.last_call=None
        self.seen_messages=0

    def act(self, observation):
        if observation.rgb is None or observation.wrist_rgb is None:
            raise ValueError('末端VLA需要真实双相机')
        robot=self.robot()
        link=robot.get_link('hand')
        quat=link.get_quat().detach().cpu().numpy()
        rotation=hand_rotation(quat)
        flange=np.asarray(observation.robot_ee)
        tcp=flange+rotation@self.tcp_offset
        rotvec=Rotation.from_matrix(rotation).as_rotvec()
        # The canonical LIBERO downward gripper branch is near +pi around x.
        if np.linalg.norm(rotvec)>3.0 and rotvec[0]<0:
            rotvec-=2*np.pi*rotvec/np.linalg.norm(rotvec)
        state=np.r_[tcp+self.translation,rotvec,observation.robot_qpos[7],-observation.robot_qpos[8]].astype(np.float32)
        messages=observation.messages[self.seen_messages:]
        self.seen_messages=len(observation.messages)
        invalidate=any(m.kind in {'assignment','correction','reassignment','activity_change','action_failed','action_blocked'} for m in messages)
        if invalidate or self.cursor>=min(len(self.chunk),self.execution_horizon):
            request={'observation/image':observation.rgb.copy(),'observation/wrist_image':observation.wrist_rgb.copy(),
                     'observation/state':state,'prompt':self.instruction}
            started=perf_counter()
            output=self.infer(request)
            chunk=np.asarray(output['actions'],dtype=float)
            if chunk.ndim!=2 or chunk.shape[1]!=7 or not np.isfinite(chunk).all():
                raise ValueError('LIBERO策略必须输出有限N×7动作')
            self.chunk,self.cursor=chunk,0
            self.calls+=1
            self.last_call={'adapter':'pi05_libero','model_call':self.calls,'raw_action_chunk':chunk.tolist(),
                            'model_input_keys':list(request),'state':state.tolist(),'prompt':self.instruction,
                            'exterior_rgb_sha256':sha256(observation.rgb.tobytes()).hexdigest(),
                            'wrist_rgb_sha256':sha256(observation.wrist_rgb.tobytes()).hexdigest(),
                            'elapsed_ms':(perf_counter()-started)*1000,'policy_translation':self.translation.tolist(),
                            'tcp_offset':self.tcp_offset.tolist(),'position_scale_m':0.05,'rotation_scale_rad':0.5}
        raw=self.chunk[self.cursor]
        self.last_call['executed_chunk_index']=self.cursor
        self.cursor+=1
        delta=np.clip(raw[:6],-1,1)
        target_rotation=Rotation.from_rotvec(delta[3:]*0.5).as_matrix()@rotation
        target_tcp=tcp+delta[:3]*0.05
        target_flange=target_tcp-target_rotation@self.tcp_offset
        xyzw=Rotation.from_matrix(target_rotation).as_quat()
        wxyz=xyzw[[3,0,1,2]]
        joints=robot.inverse_kinematics(link=link,pos=target_flange,quat=wxyz).detach().cpu().numpy()
        fingers=0.0 if raw[6]>0 else 0.04
        joints[-2:]=fingers
        self.last_call.update(current_flange=flange.tolist(),current_quaternion_wxyz=quat.tolist(),
                              target_flange=target_flange.tolist(),target_quaternion_wxyz=wxyz.tolist(),
                              solved_joint_target=joints.tolist())
        return Action('joint_position',joints=tuple(float(value) for value in joints),duration_steps=1,
                      control_mode='libero_osc_delta_to_ik')

    def audit_record(self):
        return dict(self.last_call) if self.last_call else None
