"""原生MuJoCo的动态人接触代理：力驱动指尖，显示人体不参与动力学。"""
import xml.etree.ElementTree as ET

import numpy as np

from .continuous import HumanCommand
from .human_contact import bounded_motion
from .llm_human import QwenHumanPolicy


class NativeQwenHuman(QwenHumanPolicy):
    def _system_prompt(self):
        return super()._system_prompt().replace('observe、approach、carry、yield、away、return',
                                               'observe、push、yield、away、return') + (
            '本场景是餐桌协作。你可用push意图以指尖缓慢推动指定物体到公开区域，'
            '无需先夹持；不要使用approach或carry来推动。机器人仍会根据相机放碗。'
            '任务更新和目标位置都是公开安排；具体何时推、何时观察、何时让行由你决定。'
            'message用简短英文与机器人交流，reason与memory_note用中文。'
            '不要因机器人已经放下碗就认为你移动盘子的目标也已完成。')

    def _validated_command(self, value, observation):
        if value.get('intent') == 'push':
            obj, destination = value.get('object_id'), value.get('destination')
            if obj in observation.objects and destination in observation.regions:
                return HumanCommand('push', obj, destination, speed_mps=.15, acceleration_mps2=.6)
        if value.get('intent') not in {'observe','yield','away','return'}:
            return HumanCommand('observe')
        return super()._validated_command(value, observation)


def augment_contact_human(env, destination):
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
    # Visual proxy is explicitly non-colliding. Only the force-driven fingertip contacts objects.
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
    base = ET.SubElement(world,'body',name='human_slide_x',pos='0 0 0')
    for axis, vector in [('x','1 0 0'),('y','0 1 0'),('z','0 0 1')]:
        if axis != 'x':
            base = ET.SubElement(base,'body',name='human_slide_'+axis,pos='0 0 0')
        ET.SubElement(base,'joint',name='human_'+axis,type='slide',axis=vector,
                      limited='true',range='-2 2' if axis!='z' else '.7 1.8',damping='0')
        ET.SubElement(base,'inertial',pos='0 0 0',mass='.01',diaginertia='.0001 .0001 .0001')
    hand = ET.SubElement(base,'body',name='human_fingertip',pos='0 0 0')
    ET.SubElement(hand,'geom',name='human_fingertip_contact',type='sphere',size='.015',
                  mass='.12',friction='1 .005 .0001',rgba='.70 .53 .41 1',group='1')
    actuator = root.find('actuator')
    for axis in 'xyz':
        ET.SubElement(actuator,'motor',name='human_motor_'+axis,joint='human_'+axis,
                      gear='1',ctrllimited='true',ctrlrange='-8 8')
    ET.SubElement(world,'geom',name='human_public_plate_region',type='cylinder',
                  pos=f'{destination[0]} {destination[1]} {surface_z+.0008}',size='.025 .0005',
                  rgba='.32 .64 .47 .65',contype='0',conaffinity='0',group='1')
    env.env.reset_from_xml_string(ET.tostring(root,encoding='unicode'))
    env.sim.data.qpos[:len(qpos)] = qpos
    env.sim.data.qvel[:len(qvel)] = qvel
    env.sim.data.time = old_time
    for axis, value in zip('xyz', [.25, .60, 1.12]):
        env.sim.data.set_joint_qpos('human_'+axis, value)
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
        if command.intent != 'push':
            self.signature = signature
            self.phase = 'idle' if command.intent == 'observe' else 'retreat'
            self.target = self.position().copy() if command.intent=='observe' else np.array([.25,.60,1.12])
            return
        if signature == self.signature and self.phase not in {'idle','retreat'}:
            return
        self.signature = signature
        self.object_id, self.destination = command.object_id, command.destination
        source = self.object_position(self.object_id)
        goal = np.asarray(self.regions[self.destination])
        if np.linalg.norm(source[:2]-goal[:2])<.025:
            self.phase='retreat';self.target=self.position()+[0,0,.12]
            return
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

    def physics_step(self):
        actual = self.position()
        if np.linalg.norm(actual-self.target)<.015:
            if self.phase=='approach':self.phase='descend';self.target=self.push_start.copy()
            elif self.phase=='descend':self.phase='push';self.target=self.push_end.copy()
            elif self.phase=='push':self.phase='retreat';self.target=actual+[0,0,.14]
            elif self.phase=='retreat':self.phase='idle'
        speed = .12 if self.phase=='push' else .30
        self.reference,self.velocity=bounded_motion(self.reference,self.velocity,self.target,
                                                   dt=self.dt,speed=speed,acceleration=.6)
        measured_velocity=self.env.sim.data.qvel[self.didx]
        # Critically damped force servo; all contact response remains in MuJoCo.
        force=700*(self.reference-actual)+22*(self.velocity-measured_velocity)
        force[2] += .15*9.81
        self.env.sim.data.ctrl[self.actuators]=np.clip(force,-8,8)
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
                             'object_position':self.object_position(self.object_id).tolist() if self.object_id else None,
                             'contact_geoms':contact_objects,'human_object_pose_writes':0})

    def _display(self, hand):
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
