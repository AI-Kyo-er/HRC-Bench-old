"""人专用连续运动学执行：可靠表达策略；物品附着不适用于机器人。"""
import numpy as np

from .human_contact import bounded_motion
from .native_contact_human import NativeContactHuman


class KinematicHuman(NativeContactHuman):
    def __init__(self,env,regions):
        super().__init__(env,regions)
        self.held=None;self.offset=None;self.last_request=None;self.receipts=[]
        self.motion_speed=.20;self.object_home_z={n:float(self.object_position(n)[2]) for n in env.env.objects_dict}
        self.object_q={}
        for name in env.env.objects_dict:
            body=env.env.obj_body_id[name];joint=int(env.sim.model.body_jntadr[body])
            if joint<0 or int(env.sim.model.jnt_type[joint])!=0:raise ValueError('人可操作物品必须有free joint')
            self.object_q[name]=(int(env.sim.model.jnt_qposadr[joint]),int(env.sim.model.jnt_dofadr[joint]))
        # 人身体只显示，接触球不施力；物品仍保留原生碰撞和机器人动力学。
        env.sim.model.geom_contype[self.geom]=0;env.sim.model.geom_conaffinity[self.geom]=0
        self.phase='idle';self.completed_requests=[];self.active_request=None

    def accept_choice(self,choice,request_id):
        if request_id==self.last_request:return
        self.last_request=request_id;action=choice['action'];error=None
        obj=choice.get('object_id');dest=choice.get('destination')
        if action=='pick' and self.held is not None:error='already_holding_an_object'
        if action=='place' and self.held is None:error='no_held_object'
        if action=='pick' and not error:
            grippers=set()
            for i in range(self.env.sim.data.ncon):
                c=self.env.sim.data.contact[i]
                names=[self.env.sim.model.geom_id2name(g) or '' for g in [c.geom1,c.geom2]]
                if any(n.startswith(obj+'_') for n in names):
                    grippers.update(n for n in names if n.startswith('gripper'))
            if grippers:error='object_in_robot_gripper_contact'
        self.receipts.append({'physics_time_s':float(self.env.sim.data.time),'request_id':request_id,
            'choice':choice,'accepted':error is None,'error':error})
        if error:return
        self.accepted_intent=action
        # wait继续当前运动，不自动生成新的抓放任务。
        if action=='wait':return
        self.active_request=request_id;self.object_id=obj;self.destination=dest
        if action=='pick':
            self.target=self.object_position(obj)+[0,0,.06];self.phase='pick_approach'
        elif action=='place':
            self.object_id=self.held
            self.target=np.asarray(self.regions[dest],dtype=float)-self.offset
            self.phase='place_transport'
        elif action=='point':
            self.target=self.object_position(obj)+[0,0,.10];self.phase='point'
        elif action=='move_hand':self.target=np.asarray(choice['target_xyz']);self.phase='move_hand'
        elif action in {'away','return'}:
            self.body_target=np.array([.25,.95 if action=='away' else .60])
            self.target=np.r_[self.body_target,1.12];self.phase=action

    def public_feedback(self):
        return {'implementation':'human_only_continuous_kinematic_attachment',
            'phase':self.phase,'accepted_action':self.accepted_intent,'held_object':self.held,
            'hand_xyz':self.position().tolist(),'target_xyz':self.target.tolist(),
            'remaining_distance_m':float(np.linalg.norm(self.position()-self.target)),
            'body_xy':self.body_base.tolist(),'completed_requests':self.completed_requests[-6:],
            'last_receipt':self.receipts[-1] if self.receipts else None}

    def physics_step(self):
        self.body_base,self.body_velocity=bounded_motion(self.body_base,self.body_velocity,self.body_target,
            dt=self.dt,speed=.20,acceleration=.5)
        if self.avatar is not None:self.avatar.rig.base[:2]=self.body_base
        if self.phase=='pick_approach':self.target=self.object_position(self.object_id)+[0,0,.06]
        previous=self.position()
        self.reference,self.velocity=bounded_motion(self.reference,self.velocity,self.target,
            dt=self.dt,speed=self.motion_speed,acceleration=.4)
        self.env.sim.data.qpos[self.qidx]=self.reference
        self.env.sim.data.qvel[self.didx]=self.velocity
        self.env.sim.data.ctrl[self.actuators]=0
        near=np.linalg.norm(self.reference-self.target)<.004
        if self.phase=='pick_approach' and near:
            self.held=self.object_id;self.offset=self.object_position(self.held)-self.reference
            self.target=self.reference+[0,0,.12];self.phase='pick_lift'
        elif near and self.phase=='place_transport':
            self.held=None;self.offset=None;self._complete()
        elif near and self.phase in {'pick_lift','point','move_hand','away','return'}:
            self._complete()
        write=None
        if self.held is not None:
            q,d=self.object_q[self.held];write=self.held
            self.env.sim.data.qpos[q:q+3]=self.reference+self.offset
            self.env.sim.data.qvel[d:d+3]=self.velocity;self.env.sim.data.qvel[d+3:d+6]=0
        self.physics_steps+=1
        if self.physics_steps%round(.05/self.dt)==0:self._display(self.reference)
        self.records.append({'physics_time_s':float(self.env.sim.data.time),'phase':self.phase,
            'hand_xyz':self.reference.tolist(),'hand_velocity':self.velocity.tolist(),
            'held_object':self.held,'human_attached_object_pose_write':write,
            'robot_pose_writes':0,'active_request_id':self.active_request})

    def _complete(self):
        self.completed_requests.append(self.active_request);self.phase='idle'
