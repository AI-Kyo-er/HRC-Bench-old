"""独立检查支撑/presence/反向载台；所有运行运动仅电机/动力学。"""
import copy
import json
import math
from pathlib import Path
import numpy as np
import pybullet as p
from experiments.responsive_transport_v16.world import ResponsiveWorld,CONFIG as TRANSPORT,DT

CONFIG_PATH=Path(__file__).with_name('config.json');CONFIG=json.loads(CONFIG_PATH.read_text())

def distance(t,travel,speed,ramp):
    duration=travel/speed+ramp;t=max(0,t)
    if t<ramp:return speed*t*t/(2*ramp)
    if t<duration-ramp:return speed*(t-ramp/2)
    if t<duration:return travel-speed*(duration-t)**2/(2*ramp)
    return travel

class FoundationWorld(ResponsiveWorld):
    def __init__(self,*args,**kwargs):
        self.inspection=None;self.inspection_walls=[];self.presence=None;self.presence_motion=None;self.presence_events=[]
        self.presence_target=CONFIG['presence_near_joint'];self.return_start_tick=None;self.return_origin=None;self.return_event=None;self.payload_return_event=None
        super().__init__(*args,initial_availability='ready',**kwargs)
        self.inspection=self.box(CONFIG['inspection_half_extents'],CONFIG['inspection_center'],0,(.55,.65,.75,1))
        for y in (-.06,.06):self.inspection_walls.append(self.box([.06,.005,.009],[.42,y,.019],0,(.45,.55,.65,1)))
        col=p.createCollisionShape(p.GEOM_BOX,halfExtents=CONFIG['presence_half_extents'],physicsClientId=self.client)
        vis=p.createVisualShape(p.GEOM_BOX,halfExtents=CONFIG['presence_half_extents'],rgbaColor=[.9,.6,.1,1],physicsClientId=self.client)
        self.presence=p.createMultiBody(baseMass=0,basePosition=CONFIG['presence_base'],linkMasses=[1],linkCollisionShapeIndices=[col],linkVisualShapeIndices=[vis],
            linkPositions=[[0,0,0]],linkOrientations=[[0,0,0,1]],linkInertialFramePositions=[[0,0,0]],linkInertialFrameOrientations=[[0,0,0,1]],linkParentIndices=[0],
            linkJointTypes=[p.JOINT_PRISMATIC],linkJointAxis=[[0,1,0]],physicsClientId=self.client)
        p.resetJointState(self.presence,0,CONFIG['presence_near_joint'],physicsClientId=self.client) # 仅初始化。
        self.phase='new_geometry_initialization';self.simulate(60);self.common_start_tick=self.tick;self.initial_state=copy.deepcopy(self.state())

    def goal(self,item,destination):
        if destination=='inspection':
            assert item=='blue';return CONFIG['inspection_blue_release']
        return super().goal(item,destination)

    def support_facts(self,body):
        blue=np.array(p.getBasePositionAndOrientation(self.objects['blue'],physicsClientId=self.client)[0]);vel=np.array(p.getBaseVelocity(self.objects['blue'],physicsClientId=self.client)[0])
        if body==self.partner:
            joint=p.getJointState(body,0,physicsClientId=self.client);pos=np.array(p.getLinkState(body,0,computeForwardKinematics=True,physicsClientId=self.client)[0]);bv=np.array([0,joint[1],0])
        else:pos=np.array(CONFIG['inspection_center']);bv=np.zeros(3)
        contacts=p.getContactPoints(self.objects['blue'],body,physicsClientId=self.client)
        return dict(relative_position=(blue-pos).tolist(),relative_speed=float(np.linalg.norm(vel-bv)),blue_speed=float(np.linalg.norm(vel)),
            supported=any(c[8]<=CONFIG['support_contact_max_distance_m'] and c[9]>CONFIG['support_contact_min_force_n'] for c in contacts),
            support_records=len(contacts),min_distance=min((c[8] for c in contacts),default=None),support_force=sum(c[9] for c in contacts))

    def inspection_facts(self):
        if self.inspection is None:return None
        f=self.support_facts(self.inspection);r=f['relative_position'];f['satisfied']=bool(np.linalg.norm(r[:2])<CONFIG['inspection_xy_tolerance_m'] and
            CONFIG['inspection_z_range_m'][0]<r[2]+CONFIG['inspection_center'][2]<CONFIG['inspection_z_range_m'][1] and f['blue_speed']<CONFIG['inspection_speed_m_s'] and f['supported'])
        return f

    def at_goal(self,item,destination):
        if destination=='inspection':return item=='blue' and self.inspection_facts()['satisfied']
        return super().at_goal(item,destination)

    def presence_facts(self):
        if self.presence is None:return None
        q,v=p.getJointState(self.presence,0,physicsClientId=self.client)[:2]
        return dict(joint=q,velocity=v,position=list(p.getLinkState(self.presence,0,computeForwardKinematics=True,physicsClientId=self.client)[0]),target=self.presence_target,
            near=abs(q-CONFIG['presence_near_joint'])<CONFIG['position_tolerance_m'] and abs(v)<CONFIG['stable_speed_m_s'],
            far=abs(q-CONFIG['presence_far_joint'])<CONFIG['position_tolerance_m'] and abs(v)<CONFIG['stable_speed_m_s'])

    def start_presence(self,destination):
        assert destination in ('near','far') and self.presence_motion is None
        q=p.getJointState(self.presence,0,physicsClientId=self.client)[0];target=CONFIG['presence_'+destination+'_joint']
        self.presence_motion=dict(start_tick=self.tick,origin=q,target=target,destination=destination)
        return copy.deepcopy(self.presence_motion)

    def start_return(self):
        assert self.delivery_event is not None and self.return_start_tick is None
        self.return_start_tick=self.tick;self.return_origin=p.getJointState(self.partner,0,physicsClientId=self.client)[0]
        return dict(start_tick=self.return_start_tick,origin=self.return_origin)

    def return_facts(self):
        if self.return_start_tick is None:return None
        q,v=p.getJointState(self.partner,0,physicsClientId=self.client)[:2];f=self.support_facts(self.partner);r=f['relative_position']
        carrier=abs(q-TRANSPORT['travel_m'])<CONFIG['position_tolerance_m'] and abs(v)<CONFIG['stable_speed_m_s']
        payload=carrier and f['supported'] and np.linalg.norm(r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and f['relative_speed']<TRANSPORT['blue_relative_speed_limit'] and f['blue_speed']<TRANSPORT['blue_world_speed_limit']
        return dict(carrier_joint=q,carrier_velocity=v,carrier_returned=bool(carrier),payload_returned=bool(payload),**f)

    def state(self):
        state=super().state();state.update(inspection_facts=self.inspection_facts(),presence=self.presence_facts(),presence_motion=copy.deepcopy(self.presence_motion),presence_events=copy.deepcopy(self.presence_events),
            return_start_tick=self.return_start_tick,return_origin=self.return_origin,return_event=copy.deepcopy(self.return_event),payload_return_event=copy.deepcopy(self.payload_return_event),return_facts=self.return_facts())
        return state

    def simulate(self,ticks):
        # 新方向状态独立，不临时清除正向delivery_start/event来绕过旧profile。
        for _ in range(ticks):
            if self.return_start_tick is not None:
                elapsed=(self.tick+1-self.return_start_tick)*DT;travel=TRANSPORT['travel_m']-self.return_origin
                self.partner_target=self.return_origin+distance(elapsed,travel,TRANSPORT['nominal_velocity_m_s'],TRANSPORT['ramp_seconds'])
            elif self.delivery_start_tick is not None:
                self.partner_target=TRANSPORT['travel_m']-distance((self.tick+1-self.delivery_start_tick)*DT,TRANSPORT['travel_m'],TRANSPORT['nominal_velocity_m_s'],TRANSPORT['ramp_seconds'])
            p.setJointMotorControl2(self.partner,0,p.POSITION_CONTROL,targetPosition=self.partner_target,force=100,maxVelocity=TRANSPORT['nominal_velocity_m_s'],physicsClientId=self.client)
            if self.presence is not None:
                if self.presence_motion is not None:
                    m=self.presence_motion;direction=1 if m['target']>m['origin'] else -1
                    self.presence_target=m['origin']+direction*distance((self.tick+1-m['start_tick'])*DT,abs(m['target']-m['origin']),CONFIG['presence_velocity_m_s'],CONFIG['presence_ramp_seconds'])
                p.setJointMotorControl2(self.presence,0,p.POSITION_CONTROL,targetPosition=self.presence_target,force=100,maxVelocity=CONFIG['presence_velocity_m_s'],physicsClientId=self.client)
            p.stepSimulation(physicsClientId=self.client);self.tick+=1
            facts=self.delivery_facts()
            if self.delivery_event is None and facts['satisfied']:self.delivery_event=dict(first_tick=self.tick,time_since_start=(self.tick-self.delivery_start_tick)*DT,facts=copy.deepcopy(facts),content='实际承载、相对位姿/速度及载台到位共同首次满足交付。')
            if self.presence_motion is not None:
                m=self.presence_motion;pf=self.presence_facts()
                if pf[m['destination']]:
                    self.presence_events.append(dict(kind='presence_'+m['destination'],first_tick=self.tick,motion=copy.deepcopy(m),facts=pf));self.presence_motion=None
            if self.return_start_tick is not None:
                rf=self.return_facts()
                if self.return_event is None and rf['carrier_returned']:self.return_event=dict(first_tick=self.tick,facts=copy.deepcopy(rf))
                if self.payload_return_event is None and rf['payload_returned']:self.payload_return_event=dict(first_tick=self.tick,facts=copy.deepcopy(rf))
            state=self.state();contacts=state['contacts'];self.contact_audit['total_ticks']+=1
            robot_contacts=[c for c in contacts if {c['body_a'],c['body_b']}=={self.robot,self.partner}]
            if robot_contacts:
                self.contact_audit['robot_partner_ticks']+=1;self.contact_audit['max_normal_force']=max(self.contact_audit['max_normal_force'],max(c['normal_force'] for c in robot_contacts));ph=self.contact_audit['phases'];ph[self.phase]=ph.get(self.phase,0)+1
            other=[c for c in contacts if any({c['body_a'],c['body_b']}=={self.objects[i],self.partner} for i in ('red','green'))]
            if other:
                self.object_partner_audit['ticks']+=1;self.object_partner_audit['records']+=len(other);self.object_partner_audit['max_normal_force']=max(self.object_partner_audit['max_normal_force'],max(c['normal_force'] for c in other))
                ph=self.object_partner_audit['phases'];ph[self.phase]=ph.get(self.phase,0)+1
            support=[c for c in contacts if {c['body_a'],c['body_b']}=={self.objects['blue'],self.partner}]
            self.support_audit['ticks']+=int(bool(support));self.support_audit['records']+=len(support);self.support_audit['max_normal_force']=max(self.support_audit['max_normal_force'],max((c['normal_force'] for c in support),default=0))
            if self.delivery_start_tick is not None and (self.delivery_event is None or self.delivery_event['first_tick']==self.tick):
                self.support_audit['transport_ticks']+=1;self.support_audit['transport_supported_ticks']+=int(facts['supported']);self.support_audit['max_relative_xy_error']=max(self.support_audit['max_relative_xy_error'],float(np.linalg.norm(facts['relative_position'][:2])))
            non_target=[c for c in contacts if any(i!=self.robot_target_item and {c['body_a'],c['body_b']}=={self.objects[i],self.robot} for i in self.objects)]
            if non_target:
                self.non_target_robot_audit['ticks']+=1;self.non_target_robot_audit['records']+=len(non_target);self.non_target_robot_audit['max_normal_force']=max(self.non_target_robot_audit['max_normal_force'],max(c['normal_force'] for c in non_target))
            for item in ('red','blue'):
                if item not in self.goal_first_ticks and self.at_goal(item,'left'):self.goal_first_ticks[item]=self.tick
            if self.trace:self.trace.write(json.dumps(state)+'\n')

    def wait_presence(self,destination):
        before=self.tick;self.phase='wait_presence_'+destination
        for _ in range(CONFIG['wait_budget_ticks']):
            if self.presence_facts()[destination]:break
            self.simulate(1)
        return dict(success=self.presence_facts()[destination],ticks=self.tick-before)

    def wait_return(self):
        before=self.tick;self.phase='wait_return'
        for _ in range(CONFIG['wait_budget_ticks']):
            if self.return_event is not None:break
            self.simulate(1)
        return dict(success=self.return_event is not None,payload=self.payload_return_event is not None,ticks=self.tick-before)
