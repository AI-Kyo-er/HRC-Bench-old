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
        self.transfer_destination=None;self.carried_offsets={};self.carried_quaternions={}

    def initialize_held_object(self,name):
        """仅用于第一帧前的场景初态：人持有待提供物品，不计任务贡献。"""
        self.held=name;self.object_id=name;self.offset=np.array([0.,0.,-.06])
        self.carried_offsets={name:self.offset.copy()}
        q,_=self.object_q[name]
        self.carried_quaternions={name:self.env.sim.data.qpos[q+3:q+7].copy()}
        self.env.sim.data.qpos[q:q+3]=self.position()+self.offset
        self.env.sim.forward()

    def accept_choice(self,choice,request_id):
        if request_id==self.last_request:return
        self.last_request=request_id;action=choice['action'];error=None
        obj=choice.get('object_id');dest=choice.get('destination')
        if action in {'place','relocate'} and not getattr(self.env.env,'_hrc_region_accessibility',{}).get(dest,True):
            error='destination_not_physically_accessible'
        if action=='pick' and self.held is not None:error='already_holding_an_object'
        if action=='relocate' and self.held is not None and self.held!=obj:error='holding_a_different_object'
        if action=='place' and self.held is None:error='no_held_object'
        if action in {'pick','relocate'} and not error and self.held is None:
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
        if action in {'wait','message'}:return
        # 只实现当前已选空间贡献；已在支撑位置时不反复抬起接收容器。
        if action=='relocate' and self.held is None:
            supported=False
            for i in range(self.env.sim.data.ncon):
                c=self.env.sim.data.contact[i]
                pair=[self.env.sim.model.geom_id2name(g) or '' for g in [c.geom1,c.geom2]]
                if any(g.startswith(obj+'_') for g in pair) and any(not g.startswith(('robot','gripper','human',obj+'_')) for g in pair):supported=True
            if supported and np.linalg.norm(self.object_position(obj)-np.asarray(self.regions[dest]))<.01:
                self.active_request=request_id;self.target=self.position().copy()
                self.receipts[-1]['effect']='already_at_requested_supported_position'
                self._complete();return
        if action=='relocate' and self.active_request is not None and self.phase!='idle' and obj==self.object_id and dest==self.transfer_destination:
            return
        if action=='relocate':self.body_target=np.array([.25,.60])
        self.active_request=request_id;self.object_id=obj;self.destination=dest
        self.transfer_destination=dest if action=='relocate' else None
        if action in {'pick','relocate'} and self.held is None:
            self.target=self.object_position(obj)+[0,0,.06];self.phase='pick_approach'
        elif action=='relocate':
            self.target=self.position().copy();self.target[2]=1.35;self.phase='transfer_raise'
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
            'active_request_id':self.active_request,
            'carried_objects':list(getattr(self,'carried_offsets',{})),
            'last_receipt':self.receipts[-1] if self.receipts else None}

    def physics_step(self):
        self.body_base,self.body_velocity=bounded_motion(self.body_base,self.body_velocity,self.body_target,
            dt=self.dt,speed=.20,acceleration=.5)
        if self.avatar is not None:self.avatar.rig.base[:2]=self.body_base
        if self.phase=='pick_approach':self.target=self.object_position(self.object_id)+[0,0,.06]
        if self.phase in {'transfer_translate','transfer_lower'}:
            self.target[:2]=np.asarray(self.regions[self.transfer_destination])[:2]-self.offset[:2]
            if self.phase=='transfer_lower':self.target[2]=self.regions[self.transfer_destination][2]-self.offset[2]
        previous=self.position()
        self.reference,self.velocity=bounded_motion(self.reference,self.velocity,self.target,
            dt=self.dt,speed=self.motion_speed,acceleration=.4)
        self.env.sim.data.qpos[self.qidx]=self.reference
        self.env.sim.data.qvel[self.didx]=self.velocity
        self.env.sim.data.ctrl[self.actuators]=0
        near=np.linalg.norm(self.reference-self.target)<.004
        if self.phase=='pick_approach' and near:
            self.held=self.object_id;self.offset=self.object_position(self.held)-self.reference
            self.carried_offsets={self.held:self.offset.copy()};self.carried_quaternions={}
            # 接触＋原生几何包含的载荷随人搬运容器；这是明确的人执行简化，不读取任务成绩。
            states=getattr(self.env.env,'object_states_dict',getattr(self.env.env,'object_states',{}))
            if self.held in states:
                for name in self.object_q:
                    robot_touch=False
                    for i in range(self.env.sim.data.ncon):
                        c=self.env.sim.data.contact[i]
                        pair=[self.env.sim.model.geom_id2name(g) or '' for g in [c.geom1,c.geom2]]
                        if any(g.startswith(name+'_') for g in pair) and any(g.startswith('gripper') for g in pair):robot_touch=True
                    if name!=self.held and name in states and not robot_touch and states[self.held].check_ontop(states[name]):
                        self.carried_offsets[name]=self.object_position(name)-self.reference
            for name in self.carried_offsets:
                q,_=self.object_q[name];self.carried_quaternions[name]=self.env.sim.data.qpos[q+3:q+7].copy()
            self.target=self.reference+[0,0,.12];self.phase='pick_lift'
        elif near and self.phase=='place_transport':
            self._release();self._complete()
        elif near and self.phase=='pick_lift' and getattr(self,'transfer_destination',None):
            self.target=self.reference.copy();self.target[2]=1.35;self.phase='transfer_raise'
        elif near and self.phase=='transfer_raise':
            self.target[:2]=np.asarray(self.regions[self.transfer_destination])[:2]-self.offset[:2]
            self.phase='transfer_translate'
        elif near and self.phase=='transfer_translate':
            self.target[2]=self.regions[self.transfer_destination][2]-self.offset[2];self.phase='transfer_lower'
        elif near and self.phase=='transfer_lower':
            self._release();self.target=np.r_[self.body_base,1.12];self.phase='transfer_retreat'
        elif near and self.phase in {'pick_lift','point','move_hand','away','return','transfer_retreat'}:
            self._complete()
        write=None;writes=[]
        if self.held is not None:
            write=self.held
            for name,offset in getattr(self,'carried_offsets',{self.held:self.offset}).items():
                q,d=self.object_q[name];writes.append(name)
                self.env.sim.data.qpos[q:q+3]=self.reference+offset
                if name in getattr(self,'carried_quaternions',{}):self.env.sim.data.qpos[q+3:q+7]=self.carried_quaternions[name]
                self.env.sim.data.qvel[d:d+3]=self.velocity;self.env.sim.data.qvel[d+3:d+6]=0
        self.physics_steps+=1
        if self.physics_steps%round(.05/self.dt)==0:self._display(self.reference)
        self.records.append({'physics_time_s':float(self.env.sim.data.time),'phase':self.phase,
            'hand_xyz':self.reference.tolist(),'hand_velocity':self.velocity.tolist(),
            'held_object':self.held,'human_attached_object_pose_write':write,
            'human_carried_object_pose_writes':writes,
            'robot_pose_writes':0,'active_request_id':self.active_request})

    def _complete(self):
        self.completed_requests.append(self.active_request);self.phase='idle'

    def _release(self):
        self.held=None;self.offset=None;self.carried_offsets={};self.carried_quaternions={}
