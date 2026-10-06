"""原生六自由度受力接触手：XYZ、腕部yaw、双指；无物体绑定或坐标搬运。"""
import xml.etree.ElementTree as ET

import numpy as np

from .human_contact import bounded_motion
from .native_contact_human import NativeContactHuman


def install_articulated_hand(root):
    # Effective hand/forearm inertia replaces the old 150g ungrounded fingertip.
    for axis in 'xyz':
        body=root.find(f".//body[@name='human_slide_{axis}']")
        body.find('inertial').set('mass','.10')
        body.find('joint').set('damping','2')
    hand=root.find(".//body[@name='human_fingertip']")
    tip=hand.find('geom');tip.set('mass','.70')
    ET.SubElement(hand,'joint',name='human_wrist_yaw',type='hinge',axis='0 0 1',damping='.3')
    ET.SubElement(hand,'geom',name='human_palm_contact',type='box',pos='0 .015 .04',size='.03 .03 .010',mass='.20',
                  rgba='.67 .50 .39 1',friction='1.5 .01 .001',condim='4')
    actuators=root.find('actuator')
    for motor in actuators:
        if motor.get('name','').startswith('human_motor_'):motor.set('ctrlrange','-40 40')
    ET.SubElement(actuators,'motor',name='human_motor_yaw',joint='human_wrist_yaw',gear='1',ctrllimited='true',ctrlrange='-2 2')
    for side,sign in [('left',-1),('right',1)]:
        finger=ET.SubElement(hand,'body',name='human_'+side+'_finger_body',pos=f'{sign*.010} 0 0')
        ET.SubElement(finger,'joint',name='human_'+side+'_finger',type='slide',axis=f'{sign} 0 0',
                      limited='true',range='0 .095',damping='1.0')
        ET.SubElement(finger,'geom',name='human_'+side+'_finger_contact',type='box',size='.008 .021 .006',mass='.07',
                      rgba='.72 .55 .44 1',friction='1.6 .01 .001',condim='4',solref='.02 1')
        ET.SubElement(actuators,'motor',name='human_motor_'+side+'_finger',joint='human_'+side+'_finger',
                      gear='1',ctrllimited='true',ctrlrange='-10 10')


class NativeArticulatedHuman(NativeContactHuman):
    """抓/放的运动段只执行模型已选命令；接触失败不会替策略挑选下一任务。"""
    def __init__(self,env,regions):
        super().__init__(env,regions)
        model=env.sim.model
        self.yaw_joint=model.joint_name2id('human_wrist_yaw');self.yaw_q=model.jnt_qposadr[self.yaw_joint];self.yaw_d=model.jnt_dofadr[self.yaw_joint]
        self.yaw_motor=model.actuator_name2id('human_motor_yaw')
        self.finger_joints=[model.joint_name2id('human_'+side+'_finger') for side in ['left','right']]
        self.finger_q=[model.jnt_qposadr[j] for j in self.finger_joints];self.finger_d=[model.jnt_dofadr[j] for j in self.finger_joints]
        self.finger_motors=[model.actuator_name2id('human_motor_'+side+'_finger') for side in ['left','right']]
        self.finger_geoms=[model.geom_name2id('human_'+side+'_finger_contact') for side in ['left','right']]
        self.contact_geoms={self.geom,model.geom_name2id('human_palm_contact'),*self.finger_geoms}
        self.finger_reference=np.array([.095,.095]);self.finger_target=.095;self.yaw_target=0.;self.close_dwell=0.
        self.phase_start=float(env.sim.data.time);self.motor_failure=None;self.carry_object=None
        self.mass_z=float(model.body_subtreemass[model.jnt_bodyid[self.joints[2]]])
        self.grasp_initial_object=None;self.grasp_initial_z=None

    def set_phase(self,name):
        self.phase=name;self.phase_start=float(self.env.sim.data.time)

    def finger_contacts(self,name=None):
        name=name or self.object_id;touch=[False,False]
        if not name:return touch
        for i in range(self.env.sim.data.ncon):
            contact=self.env.sim.data.contact[i]
            for k,geom in enumerate(self.finger_geoms):
                if geom in (contact.geom1,contact.geom2):
                    other=contact.geom2 if contact.geom1==geom else contact.geom1
                    if (self.env.sim.model.geom_id2name(other) or '').startswith(name+'_'):touch[k]=True
        return touch

    def accept(self,command):
        if command.intent not in {'grasp','place','release'}:
            # Observe suspends movement and preserves actual grasp pressure.
            if command.intent=='push':self.finger_target=.095
            super().accept(command)
            self.env.sim.model.geom_contype[self.geom]=int(command.intent=='push')
            self.env.sim.model.geom_conaffinity[self.geom]=int(command.intent=='push')
            return
        signature=(command.intent,command.object_id,command.destination)
        self.accepted_intent=command.intent
        if signature==self.signature and self.phase not in {'idle','holding','failed'}:return
        self.signature=signature;self.command_started_at=float(self.env.sim.data.time);self.motor_failure=None
        self.env.sim.model.geom_contype[self.geom]=0;self.env.sim.model.geom_conaffinity[self.geom]=0
        if command.intent=='release':
            self.finger_target=.095;self.set_phase('release');return
        self.object_id=command.object_id;self.destination=command.destination
        if command.intent=='grasp':
            if self.carry_object==self.object_id and all(self.finger_contacts()):return
            self.carry_object=None;self.grasp_initial_object=self.object_position(self.object_id).copy()
            self.grasp_initial_z=float(self.grasp_initial_object[2]);source=self.grasp_initial_object
            rotation=self.env.sim.data.body_xmat[self.env.env.obj_body_id[self.object_id]].reshape(3,3)
            base_yaw=float(np.arctan2(rotation[1,0],rotation[0,0]))
            choices=[]
            for yaw in [base_yaw,base_yaw+np.pi/2]:
                direction=np.array([np.cos(yaw),np.sin(yaw),0.]);extent=0.
                for name in self.env.env.objects_dict[self.object_id].contact_geoms:
                    geom=self.env.sim.model.geom_name2id(name)
                    offset=self.env.sim.data.geom_xpos[geom]-source
                    axes=self.env.sim.data.geom_xmat[geom].reshape(3,3)
                    support=(float(np.dot(np.abs(axes.T@direction),self.env.sim.model.geom_size[geom]))
                             if self.env.sim.model.geom_type[geom]==6 else float(self.env.sim.model.geom_rbound[geom]))
                    extent=max(extent,abs(float(np.dot(offset,direction)))+support)
                choices.append((extent,yaw))
            extent,self.yaw_target=min(choices)
            self.finger_target=float(np.clip(extent+.012, .012,.095));self.close_dwell=0.
            self.grasp_point=source.copy();self.grasp_point[2]=max(self.surface_z+.008,float(source[2])+.003)
            self.target=np.r_[source[:2],max(self.position()[2],self.surface_z+.16)]
            self.set_phase('grasp_approach')
        elif self.carry_object!=self.object_id:
            self.motor_failure='requested_object_not_in_measured_hand';self.set_phase('failed')
        else:
            self.target=self.position().copy();self.target[:2]=np.asarray(self.regions[self.destination])[:2]
            self.target[2]=max(self.target[2],self.surface_z+.14)
            self.set_phase('place_transfer')

    def public_feedback(self):
        result=super().public_feedback()
        result.update(contact_model='articulated_hand',supported_intents=['push','grasp','place','release','observe','yield','away','return'],
                      measured_finger_joint_positions_m=self.env.sim.data.qpos[self.finger_q].tolist(),
                      measured_finger_target_contacts=self.finger_contacts(),wrist_yaw_rad=float(self.env.sim.data.qpos[self.yaw_q]),
                      object_measured_in_hand=self.carry_object,motor_failure=self.motor_failure)
        return result

    def physics_step(self):
        self.body_base,self.body_velocity=bounded_motion(self.body_base,self.body_velocity,self.body_target,dt=self.dt,speed=.20,acceleration=.5)
        if self.avatar is not None:self.avatar.rig.base[:2]=self.body_base
        if self.phase=='navigate':
            self.target=np.r_[self.body_base,1.12]
            if np.linalg.norm(self.body_base-self.body_target)<.01:self.phase='idle'
        actual=self.position();near=np.linalg.norm(actual-self.target)<.010
        elapsed=float(self.env.sim.data.time)-self.phase_start
        if self.phase=='grasp_approach' and near:
            self.target=self.grasp_point.copy();self.set_phase('grasp_descend')
        elif self.phase=='grasp_descend' and near:
            self.finger_target=0.;self.set_phase('grasp_close')
        elif self.phase=='grasp_close':
            self.close_dwell=self.close_dwell+self.dt if all(self.finger_contacts()) else 0.
            if self.close_dwell>=.10:
                self.target=actual+[0,0,.12];self.set_phase('grasp_lift')
            elif elapsed>5.:
                self.motor_failure='no_bilateral_contact';self.set_phase('failed')
        elif self.phase=='grasp_lift' and near:
            if all(self.finger_contacts()) and self.object_position(self.object_id)[2]>self.grasp_initial_z+.04:
                self.carry_object=self.object_id;self.set_phase('holding')
            else:self.motor_failure='contact_or_lift_not_retained';self.set_phase('failed')
        elif self.phase=='place_transfer' and near:
            self.target=actual.copy();self.target[2]=self.grasp_point[2]+(self.regions[self.destination][2]-self.grasp_initial_z)+.003;self.set_phase('place_lower')
        elif self.phase=='place_lower' and near:
            self.finger_target=.095;self.set_phase('release')
        elif self.phase=='release' and np.min(self.env.sim.data.qpos[self.finger_q])>.06:
            self.carry_object=None;self.target=actual+[0,0,.12];self.set_phase('grasp_retreat')
        elif self.phase=='grasp_retreat' and near:self.set_phase('idle')
        elif near:
            if self.phase=='approach':self.phase='descend';self.target=self.push_start.copy()
            elif self.phase=='descend':self.phase='push';self.target=self.push_end.copy()
            elif self.phase=='push':self._retreat(actual)
            elif self.phase=='retreat':self.phase='idle'
        speed=.10 if self.phase in {'push','grasp_descend','place_lower'} else .20
        self.reference,self.velocity=bounded_motion(self.reference,self.velocity,self.target,dt=self.dt,speed=speed,acceleration=.4)
        desired=self.velocity+4*(self.reference-actual);desired*=min(1.,speed/max(np.linalg.norm(desired),1e-12))
        measured=self.env.sim.data.qvel[self.didx].copy()
        force=90*(desired-measured);force[2]+=-self.mass_z*self.env.sim.model.opt.gravity[2]
        force=np.clip(force,-40,40);self.env.sim.data.ctrl[self.actuators]=force
        yaw=float(self.env.sim.data.qpos[self.yaw_q]);error=np.arctan2(np.sin(self.yaw_target-yaw),np.cos(self.yaw_target-yaw))
        self.env.sim.data.ctrl[self.yaw_motor]=np.clip(.3*(np.clip(4*error,-.7,.7)-self.env.sim.data.qvel[self.yaw_d]),-2,2)
        self.finger_reference+=np.clip(self.finger_target-self.finger_reference,-.025*self.dt,.025*self.dt)
        self.env.sim.data.ctrl[self.finger_motors]=np.clip(200*(self.finger_reference-self.env.sim.data.qpos[self.finger_q])-7*self.env.sim.data.qvel[self.finger_d],-10,10)
        self.physics_steps+=1
        if self.physics_steps%round(.05/self.dt)==0:self._display(actual)
        contacts=[]
        for i in range(self.env.sim.data.ncon):
            c=self.env.sim.data.contact[i]
            if c.geom1 in self.contact_geoms or c.geom2 in self.contact_geoms:
                other=c.geom2 if c.geom1 in self.contact_geoms else c.geom1
                contacts.append(self.env.sim.model.geom_id2name(other))
        self.records.append({'physics_time_s':float(self.env.sim.data.time),'phase':self.phase,'object_id':self.object_id,
            'destination':self.destination,'actual_position':actual.tolist(),'actual_velocity':measured.tolist(),
            'reference':self.reference.tolist(),'motor_force_n':force.tolist(),'body_position':self.body_base.tolist(),
            'body_velocity':self.body_velocity.tolist(),'object_position':self.object_position(self.object_id).tolist() if self.object_id else None,
            'contact_geoms':contacts,'human_object_pose_writes':0,'contact_model':'articulated_hand',
            'finger_joint_positions_m':self.env.sim.data.qpos[self.finger_q].tolist(),
            'finger_target_contacts':self.finger_contacts(),'measured_carry_object':self.carry_object,'motor_failure':self.motor_failure})
