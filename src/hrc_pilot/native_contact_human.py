"""原生MuJoCo的动态人接触代理：力驱动指尖，显示人体不参与动力学。"""
import xml.etree.ElementTree as ET

import numpy as np

from .continuous import HumanCommand
from .human_contact import bounded_motion
from .llm_human import QwenHumanPolicy, PERSONAS
from .native_action_validation import command_feedback
from .native_contact_observation import own_contact_observation
import json


class NativeQwenHuman(QwenHumanPolicy):
    generation_token_limit = 384

    def reset(self, seed):
        super().reset(seed)
        self.generated_plan=[]
        self.motor_observation_history=[]
        self.wait_condition=''
        self.last_command_feedback=None

    def _prompt(self, observation):
        visible=json.loads(super()._prompt(observation).split('\n',1)[1])
        measured={'time_s':observation.time_s,'human':observation.human_execution,
                  'robot':observation.robot_motion}
        self.motor_observation_history.append(measured)
        visible.update(your_measured_execution=observation.human_execution,
                       robot_measured_motion=observation.robot_motion,
                       your_measured_execution_history=self.motor_observation_history[-6:],
                       your_previous_generated_plan=self.generated_plan,
                       your_previous_wait_condition=self.wait_condition,
                       your_last_command_validation=self.last_command_feedback,
                       your_current_assignments=[item for item in self.public_task_memory.values() if item['assigned_role']=='human'],
                       robot_current_assignments=[item for item in self.public_task_memory.values() if item['assigned_role']=='robot'],
                       action_interface={'intents':['push','observe','yield','away','return'],
                                         'push_object_id_values':list(observation.objects),
                                         'push_destination_values':list(observation.regions)},
                       memory_semantics='memory_note是你写下的解释，不是执行成功证明；当前测量与执行历史优先。')
        return '根据公开分工和实际执行反馈，更新自己的目标与计划并选择一个当前动作：\n'+json.dumps(visible,ensure_ascii=False,separators=(',',':'))

    def step(self, observation):
        count=len(self.policy_io)
        output=super().step(observation)
        if len(self.policy_io)>count and self.policy_io[-1]['parse_error'] is None:
            value=self._parse(self.policy_io[-1]['raw_output'])
            plan=value.get('plan',[])
            if isinstance(plan,list):self.generated_plan=[str(item)[:180] for item in plan[:5]]
            self.wait_condition=str(value.get('wait_condition',''))[:300]
            self.policy_io[-1]['generated_plan']=self.generated_plan.copy()
            self.policy_io[-1]['wait_condition']=self.wait_condition
            self.policy_io[-1]['command_validation']=self.last_command_feedback
        return output

    def audit_state(self):
        return {**super().audit_state(),'generated_plan':self.generated_plan,
                'measured_execution_history':self.motor_observation_history,'wait_condition':self.wait_condition}

    def _system_prompt(self):
        return (
            '你是正在与机械臂共同准备餐桌的人。你有自己的较长期工作目标，'
            '根据当前公开任务板、可见进展、自身经历和机械臂的活动，自主选择下一步行动。'
            f'你的稳定行为倾向：{PERSONAS[self.persona_id]} '
            'objects_xyz、regions_xyz和your_hand_position_xyz是本时刻可靠的感知坐标，'
            '可以直接用于动作选择。它们已经给出了物体与区域的位置。'
            '任务板assigned_role为human属于你，为robot属于机械臂；人的对象和目的地可以随公开安排改变；当前任务板分别规定你和机械臂的工作。'
            '机械臂的活动不表示人的工作已经完成，也不表示必须在任何情况下等待。'
            '支持的意图为push、observe、yield、away、return。'
            'push指定一个当前可见物体和公开区域，执行器会连续接近并通过指尖受力推动，'
            '不需要先夹持；执行过程可能因碰撞偏离，你可以根据后续观察继续、暂停或重新选择。'
            'observe保持位置并观察，yield小幅退让，away退离工作台，return回到原工作位置；'
            '身体通过连续步行动作移动，手随身体清离或返回。'
            '本执行器不支持抓持，不输出approach或carry。'
            '你可以因空间冲突、个人优先事项、进展或风险改变当前计划，具体时机和动作由你决定。'
            'current_goal描述你希望实现的较长期工作结果；观察、推和让行是推进目标的当前动作。'
            'recent_public_decisions和旧经验是过去的计划与记录，当前坐标优先用于判断现在的位置；'
            '经验中的旧位置不能当成当前位置。观察等待时，在reason中说明当前等待的理由或条件。'
            '先理解公开分工和依赖，自己在plan中列出接下来几步；每次依据测量决定继续、调整或放弃。'
            'your_measured_execution报告实际身体、手、物体位置和剩余距离；发出命令并不代表到达。'
            'running表示低层动作还在执行，observe会中断当前动作并保持原地，继续动作需再次选同一意图。'
            'motor_finished只表示运动原语结束，不保证物体到达目标；请检查物体位置和剩余距离。'
            'robot_measured_motion只描述可见运动，不能当作机器人已完成或已理解等待的证明。'
            '当计划与实际反馈不一致时，依据当前位置重新规划；不要把过去写下的已返回等文字当成事实。'
            '若选择等待，wait_condition写具体可观察条件；持续没有该条件时可询问或重新协调。'
            'your_last_command_validation给出上一请求是否被接受及拒绝理由，rejected表示该动作没有执行。'
            'action_interface列出本时刻合法参数，object_id是物体名，destination必须是区域名，不能拿物体名当区域名。'
            'your_current_assignments是你的工作，robot_current_assignments是机械臂的工作；改变分工需要公开协调。'
            '只输出JSON对象：intent、object_id、destination、message、speed_mps、reason、memory_note、current_goal、plan、wait_condition。'
            'message用简短英文与机器人交流，reason、memory_note和current_goal用中文。'
            'memory_note只记录有新观察依据的经验，不写机械臂隐藏计划或评测分数。'
            '不需要读取任何未公开的任务标签、机器人计划或评测器。')

    def _validated_command(self, value, observation):
        command=self._native_command(value,observation)
        self.last_command_feedback=command_feedback(value,command,observation.objects,observation.regions)
        return command

    def _native_command(self, value, observation):
        if value.get('intent') == 'push':
            obj, destination = value.get('object_id'), value.get('destination')
            if obj in observation.objects and destination in observation.regions:
                return HumanCommand('push', obj, destination, speed_mps=.15, acceleration_mps2=.6)
        if value.get('intent') not in {'observe','yield','away','return'}:
            return HumanCommand('observe')
        return super()._validated_command(value, observation)


def augment_contact_human(env, destination, *, visualization='vico_skin', public_regions=None, contact_model='fingertip', raised_storage=False):
    """仅初始化时重编译场景，并按名字保持原机器人/物体qpos与qvel。"""
    old_model, old_data = env.sim.model, env.sim.data
    qpos, qvel = old_data.qpos.copy(), old_data.qvel.copy()
    old_time = float(old_data.time)
    root = ET.fromstring(old_model.get_xml())
    world = root.find('worldbody')
    table=old_model.geom_name2id('table_collision')
    surface_z=float(old_data.geom_xpos[table,2]+old_model.geom_size[table,2])
    from scipy.spatial.transform import Rotation
    eye=np.array([1.40,-1.20,1.65]);forward=np.array([0.,.20,1.0])-eye
    forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    quaternion=Rotation.from_matrix(np.column_stack([right,up,-forward])).as_quat()
    ET.SubElement(world,'camera',name='hrc_view',pos=' '.join(map(str,eye)),
                  quat=' '.join(map(str,np.r_[quaternion[3],quaternion[:3]])),fovy='52')
    # Visual skin is not a physical actuator. The fingertip remains force driven.
    rig=None
    if visualization=='vico_skin':
        from .native_avatar import AvatarRig, add_avatar
        rig=AvatarRig();add_avatar(root,rig)
    elif visualization=='capsule':
        body = ET.SubElement(world, 'body', name='human_display', mocap='true', pos='.25 .60 0')
        for name, kind, pos, size, rgba in [
            ('human_torso','capsule','0 0 1.20','.105 .23','.18 .27 .36 1'),
            ('human_head','sphere','0 0 1.65','.095','.70 .53 .41 1'),
            ('human_leg_left','capsule','-.09 0 .46','.055 .38','.22 .25 .28 1'),
            ('human_leg_right','capsule','.09 0 .46','.055 .38','.22 .25 .28 1')]:
            ET.SubElement(body,'geom',name=name,type=kind,pos=pos,size=size,rgba=rgba,
                          contype='0',conaffinity='0',group='1')
        for name, length, rgba in [('human_upper_arm',.36,'.18 .27 .36 1'),
                                   ('human_forearm',.33,'.70 .53 .41 1')]:
            segment = ET.SubElement(world,'body',name=name,mocap='true',pos='.25 .60 1.3')
            ET.SubElement(segment,'geom',name=name+'_visual',type='capsule',size=f'.032 {length/2}',
                          rgba=rgba,contype='0',conaffinity='0',group='1')
    else:raise ValueError('未知人体显示资产')
    base = ET.SubElement(world,'body',name='human_slide_x',pos='0 0 0')
    for axis, vector in [('x','1 0 0'),('y','0 1 0'),('z','0 0 1')]:
        if axis != 'x':
            base = ET.SubElement(base,'body',name='human_slide_'+axis,pos='0 0 0')
        ET.SubElement(base,'joint',name='human_'+axis,type='slide',axis=vector,
                      limited='true',range='-2 2' if axis!='z' else '.7 1.8',damping='0')
        ET.SubElement(base,'inertial',pos='0 0 0',mass='.01',diaginertia='.0001 .0001 .0001')
    hand = ET.SubElement(base,'body',name='human_fingertip',pos='0 0 0')
    ET.SubElement(hand,'geom',name='human_fingertip_contact',type='sphere',size='.015',
                  mass='.12',friction='1 .005 .0001',rgba='.70 .53 .41 0' if rig else '.70 .53 .41 1',group='1')
    actuator = root.find('actuator')
    for axis in 'xyz':
        ET.SubElement(actuator,'motor',name='human_motor_'+axis,joint='human_'+axis,
                      gear='1',ctrllimited='true',ctrlrange='-8 8')
    ET.SubElement(world,'geom',name='human_public_plate_region',type='cylinder',
                  pos=f'{destination[0]} {destination[1]} {surface_z+.0008}',size='.025 .0005',
                  rgba='.32 .64 .47 .65',contype='0',conaffinity='0',group='1')
    if raised_storage:
        point=public_regions['cookies_shelf']
        ET.SubElement(world,'geom',name='human_storage_support',type='box',pos=f'{point[0]} {point[1]} {surface_z+.04}',
                      size='.07 .07 .04',rgba='.55 .38 .22 1',friction='1 .01 .001')
    if public_regions:
        colors={'plate_ready':'.32 .64 .47 .65','plate_home':'.24 .47 .85 .65',
                'cookies_ready':'.92 .57 .20 .65','cookies_home':'.62 .35 .76 .65'}
        for name,point in public_regions.items():
            if name in {'near_human','plate_shelf'}:continue
            # plate_ready aliases the existing green marker; no duplicate z-fighting.
            if name=='plate_ready' or np.linalg.norm(np.asarray(point)[:2]-np.asarray(destination)[:2])<1e-8:continue
            ET.SubElement(world,'geom',name='human_public_region_'+name,type='cylinder',
                          pos=f'{point[0]} {point[1]} {surface_z+.0808 if name=="cookies_shelf" else surface_z+.0008}',size='.025 .0005',
                          rgba=colors.get(name,'.24 .47 .85 .65' if name.endswith('_home') else '.32 .64 .47 .65' if name.endswith('_personal') else '.83 .64 .26 .65'),contype='0',conaffinity='0',group='1')
    if contact_model=='articulated_hand':
        from .native_articulated_hand import install_articulated_hand
        install_articulated_hand(root)
    elif contact_model!='fingertip':raise ValueError('未知原生接触手类型')
    env.env.reset_from_xml_string(ET.tostring(root,encoding='unicode'))
    env.env._hrc_avatar_rig=rig
    env.sim.data.qpos[:len(qpos)] = qpos
    env.sim.data.qvel[:len(qvel)] = qvel
    env.sim.data.time = old_time
    for axis, value in zip('xyz', [.25, .60, 1.12]):
        env.sim.data.set_joint_qpos('human_'+axis, value)
    if contact_model=='articulated_hand':
        for side in ['left','right']:env.sim.data.set_joint_qpos('human_'+side+'_finger',.095)
    env.sim.forward()
    env.env._update_observables(force=True)
    return env.env._get_observations()


class NativeContactHuman:
    """接近/下降/推/清离是运动原语，任务与时机来自生成式伙伴。"""
    def __init__(self, env, regions):
        self.env, self.regions = env, regions
        self.joints = [env.sim.model.joint_name2id('human_'+axis) for axis in 'xyz']
        self.qidx = [env.sim.model.jnt_qposadr[j] for j in self.joints]
        self.didx = [env.sim.model.jnt_dofadr[j] for j in self.joints]
        self.actuators = [env.sim.model.actuator_name2id('human_motor_'+axis) for axis in 'xyz']
        self.geom = env.sim.model.geom_name2id('human_fingertip_contact')
        table=env.sim.model.geom_name2id('table_collision')
        self.surface_z=float(env.sim.data.geom_xpos[table,2]+env.sim.model.geom_size[table,2])
        self.reference = self.position().copy()
        self.velocity = np.zeros(3)
        self.phase, self.object_id, self.destination = 'idle', None, None
        self.signature = None
        self.target = self.reference.copy()
        self.dt = float(env.sim.model.opt.timestep)
        self.records = []
        self.retreat_signature=None
        self.destination_radius=float(env.sim.model.geom_size[env.sim.model.geom_name2id('human_public_plate_region'),0])
        self.accepted_intent='observe'
        self.command_started_at=float(env.sim.data.time)
        self.physics_steps=0
        self.avatar=None
        self.body_base=np.array([.25,.60]);self.body_target=self.body_base.copy();self.body_velocity=np.zeros(2)
        if getattr(env.env,'_hrc_avatar_rig',None) is not None:
            from .native_avatar import NativeAvatarDisplay
            self.avatar=NativeAvatarDisplay(env,env.env._hrc_avatar_rig)
        original = env.env._pre_action
        def pre_action(action, policy_step=False):
            original(action, policy_step=policy_step)
            self.physics_step()
        env.env._pre_action = pre_action

    def position(self):
        return self.env.sim.data.qpos[self.qidx].copy()

    def object_position(self, name):
        return self.env.sim.data.body_xpos[self.env.env.obj_body_id[name]].copy()

    def accept(self, command):
        signature = (command.intent, command.object_id, command.destination)
        if signature!=self.signature:
            self.command_started_at=float(self.env.sim.data.time)
        self.accepted_intent=command.intent
        if command.intent != 'push':
            self.signature = signature
            if command.intent in {'yield','away','return'}:
                self.body_target=np.array([.25,{'yield':.75,'away':.95,'return':.60}[command.intent]])
                self.phase='navigate'
            else:
                self.body_target=self.body_base.copy();self.phase='idle'
            self.target = self.position().copy() if command.intent=='observe' else np.array([.25,.60,1.12])
            return
        if signature == self.signature and self.phase not in {'idle','retreat'}:
            return
        self.signature = signature
        self.object_id, self.destination = command.object_id, command.destination
        self.body_target=np.array([.25,.60])
        source = self.object_position(self.object_id)
        goal = np.asarray(self.regions[self.destination])
        if np.linalg.norm(source[:2]-goal[:2])<self.destination_radius:
            if self.retreat_signature!=signature:
                self.retreat_signature=signature;self._retreat(self.position())
            return
        self.retreat_signature=None
        direction = goal[:2]-source[:2]
        self.direction = direction/np.linalg.norm(direction)
        model = self.env.env.objects_dict[self.object_id]
        # Placement metadata is not the collision footprint. Use conservative
        # support from actual collision geoms so descent starts outside the rim.
        supports=[]
        for name in model.contact_geoms:
            geom=self.env.sim.model.geom_name2id(name)
            offset=self.env.sim.data.geom_xpos[geom][:2]-source[:2]
            supports.append(-np.dot(offset,self.direction)+self.env.sim.model.geom_rbound[geom])
        self.radius=max(supports)+.016
        self.push_start = source.copy()
        self.push_start[:2] -= self.direction*self.radius
        self.push_start[2] = self.surface_z+.016
        self.push_end = self.push_start.copy()
        self.push_end[:2] += goal[:2]-source[:2]+self.direction*.02
        self.phase='approach'
        self.target=self.push_start+[0,0,.14]

    def _retreat(self, actual):
        self.phase='retreat';self.target=actual.copy()
        self.target[2]=max(float(actual[2]),self.surface_z+.16)

    def destination_position(self):
        return np.asarray(self.regions[self.destination]) if self.destination in self.regions else None

    def public_feedback(self):
        """实际执行器测量；无任务标签、私有评分或策略动作建议。"""
        body_distance=float(np.linalg.norm(self.body_base-self.body_target))
        hand_distance=float(np.linalg.norm(self.position()-self.target))
        running=self.phase!='idle' or body_distance>.01 or hand_distance>.02
        result={'accepted_intent':self.accepted_intent,'motor_phase':self.phase,
                'status':'holding_position' if self.accepted_intent=='observe' else ('running' if running else 'motor_finished'),
                'command_elapsed_s':float(self.env.sim.data.time)-self.command_started_at,
                'body_xy':self.body_base.tolist(),'body_target_xy':self.body_target.tolist(),
                'body_remaining_distance_m':body_distance,'fingertip_xyz':self.position().tolist(),
                'fingertip_target_xyz':self.target.tolist(),'fingertip_remaining_distance_m':hand_distance}
        data=self.env.sim.data
        if hasattr(data,'ncon'):
            pairs=[{'geom1':self.env.sim.model.geom_id2name(data.contact[i].geom1),
                    'geom2':self.env.sim.model.geom_id2name(data.contact[i].geom2),
                    'distance_m':float(data.contact[i].dist)} for i in range(data.ncon)]
            result['hand_contact_report']=own_contact_observation(pairs,'human')
            result['hand_contact_geoms']=result['hand_contact_report']['contact_geoms']
            result['actual_hand_velocity_m_s']=data.qvel[self.didx].tolist()
            result['hand_motor_command_force_n']=data.ctrl[self.actuators].tolist()
        point=self.destination_position()
        if self.object_id is not None and point is not None:
            actual=self.object_position(self.object_id)
            result.update(object_id=self.object_id,destination=self.destination,
                          object_xyz=actual.tolist(),destination_xyz=point.tolist(),
                          object_remaining_xy_distance_m=float(np.linalg.norm(actual[:2]-point[:2])))
            radius=getattr(self,'destination_radius',.025)
            result['visible_destination_radius_m']=radius
            result['object_center_inside_visible_destination']=result['object_remaining_xy_distance_m']<radius
        return result

    def physics_step(self):
        self.body_base,self.body_velocity=bounded_motion(self.body_base,self.body_velocity,self.body_target,
                                                        dt=self.dt,speed=.25,acceleration=.6)
        if self.avatar is not None:self.avatar.rig.base[:2]=self.body_base
        if self.phase=='navigate':
            self.target=np.r_[self.body_base,1.12]
            if np.linalg.norm(self.body_base-self.body_target)<.01:self.phase='idle'
        actual = self.position()
        if np.linalg.norm(actual-self.target)<.015:
            if self.phase=='approach':self.phase='descend';self.target=self.push_start.copy()
            elif self.phase=='descend':self.phase='push';self.target=self.push_end.copy()
            elif self.phase=='push':self._retreat(actual)
            elif self.phase=='retreat':self.phase='idle'
        speed = .12 if self.phase=='push' else .30
        self.reference,self.velocity=bounded_motion(self.reference,self.velocity,self.target,
                                                   dt=self.dt,speed=speed,acceleration=.6)
        measured_velocity=self.env.sim.data.qvel[self.didx]
        # Critically damped force servo; all contact response remains in MuJoCo.
        force=700*(self.reference-actual)+22*(self.velocity-measured_velocity)
        force[2] += .15*9.81
        self.env.sim.data.ctrl[self.actuators]=np.clip(force,-8,8)
        self.physics_steps+=1
        # Pose immediately before each camera update; at most 2ms of hand lag.
        if self.avatar is None or self.physics_steps%round(.05/self.dt)==0:
            self._display(actual)
        contact_objects=[]
        for index in range(self.env.sim.data.ncon):
            c=self.env.sim.data.contact[index]
            if self.geom in (c.geom1,c.geom2):
                other=c.geom2 if c.geom1==self.geom else c.geom1
                contact_objects.append(self.env.sim.model.geom_id2name(other))
        self.records.append({'physics_time_s':float(self.env.sim.data.time),'phase':self.phase,
                             'object_id':self.object_id,'destination':self.destination,
                             'actual_position':actual.tolist(),'actual_velocity':measured_velocity.tolist(),
                             'reference':self.reference.tolist(),'motor_force_n':np.clip(force,-8,8).tolist(),
                             'body_position':self.body_base.tolist(),'body_velocity':self.body_velocity.tolist(),
                             'object_position':self.object_position(self.object_id).tolist() if self.object_id else None,
                             'contact_geoms':contact_objects,'human_object_pose_writes':0})

    def _display(self, hand):
        if self.avatar is not None:
            self.avatar.update(hand,initialise=not self.avatar.records,walking=np.linalg.norm(self.body_velocity)>.01)
            return
        shoulder=np.array([.25,.60,1.42])
        direction=hand-shoulder;distance=np.linalg.norm(direction)
        elbow=(shoulder+hand)/2
        elbow[0]+=np.sqrt(max(.01,.35**2-min(distance/2,.35)**2))
        for name,a,b in [('human_upper_arm',shoulder,elbow),('human_forearm',elbow,hand)]:
            body=self.env.sim.model.body_name2id(name)
            mocap=self.env.sim.model.body_mocapid[body]
            axis=b-a;axis/=max(np.linalg.norm(axis),1e-10)
            quaternion=np.r_[1+axis[2],np.cross([0,0,1],axis)]
            if np.linalg.norm(quaternion)<1e-8:quaternion=np.array([0.,1,0,0])
            quaternion/=np.linalg.norm(quaternion)
            self.env.sim.data.mocap_pos[mocap]=(a+b)/2
            self.env.sim.data.mocap_quat[mocap]=quaternion
