"""新循环World；旧父源不改，每tick原电机/摩擦动力学。"""
import copy
import json
from pathlib import Path
import numpy as np
import pybullet as p
from experiments.structure_foundation_v20.world_v1 import FoundationWorld,distance,CONFIG as GEOMETRY,TRANSPORT,DT
from experiments.transport_cycle_v22.cycle import CycleLedger

CONFIG=json.loads(Path(__file__).with_name('config.json').read_text())


class CycleWorld(FoundationWorld):
    def __init__(self,*args,**kwargs):
        self.cycle=CycleLedger()
        super().__init__(*args,**kwargs)

    def carrier_facts(self):
        q,v=p.getJointState(self.partner,0,physicsClientId=self.client)[:2]
        f=self.support_facts(self.partner);r=f['relative_position']
        leg=self.cycle.legs[self.cycle.active-1] if self.cycle.active is not None else None
        finished=leg is None or (self.tick-leg['start_tick'])*DT >= abs(leg['target']-leg['origin'])/TRANSPORT['nominal_velocity_m_s']+TRANSPORT['ramp_seconds']
        return dict(tick=self.tick,joint=q,velocity=v,profile_finished=finished,
            near=abs(q)<GEOMETRY['position_tolerance_m'] and abs(v)<GEOMETRY['stable_speed_m_s'],
            far=abs(q-TRANSPORT['travel_m'])<GEOMETRY['position_tolerance_m'] and abs(v)<GEOMETRY['stable_speed_m_s'],
            payload_stable=bool(f['supported'] and np.linalg.norm(r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and
                TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and
                f['relative_speed']<TRANSPORT['blue_relative_speed_limit'] and f['blue_speed']<TRANSPORT['blue_world_speed_limit']),**f)

    def request_motion(self,direction):
        result=self.cycle.request(direction,self.carrier_facts())
        if result['decision']=='accepted':
            if direction=='forward' and self.delivery_start_tick is None:self.delivery_start_tick=self.tick
            if direction=='return' and self.return_start_tick is None:
                self.return_start_tick=self.tick;self.return_origin=self.carrier_facts()['joint']
        return result

    def start_delivery(self):
        return self.request_motion('forward')

    def start_return(self):
        return self.request_motion('return')

    def goal(self,item,destination):
        if destination=='carrier':
            assert item=='blue';return CONFIG['reload_release']
        return super().goal(item,destination)

    def at_goal(self,item,destination):
        if destination=='carrier':
            f=self.carrier_facts();return item=='blue' and f['near'] and f['payload_stable']
        return super().at_goal(item,destination)

    def pick_place(self,item,destination,route='direct'):
        if item=='blue':
            f=self.carrier_facts();regions=[r for r in ('inspection','left','right') if self.at_goal('blue',r)]
            if self.cycle.active is not None or not (regions or (f['near'] and f['payload_stable'])):
                return dict(success=False,physical_attempt=False,reason='blue当前来源非核验稳定近端载台/盘/检查台，或载台正在运动。')
            if destination=='carrier' and not f['near']:
                return dict(success=False,physical_attempt=False,reason='重装须载台当前实际近端稳定。')
        return super().pick_place(item,destination,route)

    def state(self):
        s=super().state();s.update(cycle=self.cycle.snapshot(),current_carrier_facts=self.carrier_facts())
        return s

    def simulate(self,ticks):
        for _ in range(ticks):
            if self.cycle.active is not None:
                leg=self.cycle.legs[self.cycle.active-1];delta=leg['target']-leg['origin'];sign=1 if delta>0 else -1
                self.partner_target=leg['origin']+sign*distance((self.tick+1-leg['start_tick'])*DT,abs(delta),TRANSPORT['nominal_velocity_m_s'],TRANSPORT['ramp_seconds'])
            p.setJointMotorControl2(self.partner,0,p.POSITION_CONTROL,targetPosition=self.partner_target,force=100,
                                   maxVelocity=TRANSPORT['nominal_velocity_m_s'],physicsClientId=self.client)
            if self.presence is not None:
                # 本批presence没有运动，但所有几何同时存在。
                p.setJointMotorControl2(self.presence,0,p.POSITION_CONTROL,targetPosition=self.presence_target,
                    force=100,maxVelocity=GEOMETRY['presence_velocity_m_s'],physicsClientId=self.client)
            p.stepSimulation(physicsClientId=self.client);self.tick+=1
            facts=self.carrier_facts();self.cycle.sample(facts)
            # 父历史字段保留第一实际贡献；新循环只使用cycle编号/当前事实。
            for leg in self.cycle.legs:
                if leg['direction']=='forward' and self.delivery_event is None and leg['payload_event'] is not None:
                    self.delivery_event=dict(first_tick=leg['payload_event']['first_tick'],leg_id=leg['id'],facts=copy.deepcopy(facts))
                if leg['direction']=='return':
                    if self.return_event is None and leg['carrier_event'] is not None:self.return_event=copy.deepcopy(leg['carrier_event'])
                    if self.payload_return_event is None and leg['payload_event'] is not None:self.payload_return_event=copy.deepcopy(leg['payload_event'])
            state=self.state()
            if self.trace:self.trace.write(json.dumps(state)+'\n')
