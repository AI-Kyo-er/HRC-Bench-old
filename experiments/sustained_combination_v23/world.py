"""循环运输与真实presence在同tick推进，物理后采样检查服务。"""
import copy
import gzip
import json
import pybullet as p
from experiments.transport_cycle_v22.world import CycleWorld,TRANSPORT,GEOMETRY,DT,distance


class CombinationWorld(CycleWorld):
    def __init__(self,*args,service_trace_path=None,**kwargs):
        self.step_callback=None;self.service_trace=None
        super().__init__(*args,**kwargs)
        if service_trace_path:self.service_trace=gzip.open(service_trace_path,'wt')

    def public_inspection_sample(self):
        state=self.state()
        contacts=[c for c in state['contacts'] if {c['body_a'],c['body_b']}=={self.robot,self.objects['blue']}]
        return dict(tick=self.tick,inspection=state['inspection_facts'],presence=state['presence'],
                    presence_moving=state['presence_motion'] is not None,robot_blue_contact=bool(contacts),robot_blue_contacts=contacts)

    def simulate(self,ticks):
        for _ in range(ticks):
            if self.cycle.active is not None:
                leg=self.cycle.legs[self.cycle.active-1];delta=leg['target']-leg['origin'];sign=1 if delta>0 else -1
                self.partner_target=leg['origin']+sign*distance((self.tick+1-leg['start_tick'])*DT,abs(delta),TRANSPORT['nominal_velocity_m_s'],TRANSPORT['ramp_seconds'])
            p.setJointMotorControl2(self.partner,0,p.POSITION_CONTROL,targetPosition=self.partner_target,force=100,
                maxVelocity=TRANSPORT['nominal_velocity_m_s'],physicsClientId=self.client)
            if self.presence is not None:
                if self.presence_motion is not None:
                    motion=self.presence_motion;sign=1 if motion['target']>motion['origin'] else -1
                    self.presence_target=motion['origin']+sign*distance((self.tick+1-motion['start_tick'])*DT,
                        abs(motion['target']-motion['origin']),GEOMETRY['presence_velocity_m_s'],GEOMETRY['presence_ramp_seconds'])
                p.setJointMotorControl2(self.presence,0,p.POSITION_CONTROL,targetPosition=self.presence_target,force=100,
                    maxVelocity=GEOMETRY['presence_velocity_m_s'],physicsClientId=self.client)
            p.stepSimulation(physicsClientId=self.client);self.tick+=1
            facts=self.carrier_facts();self.cycle.sample(facts)
            for leg in self.cycle.legs:
                if leg['direction']=='forward' and self.delivery_event is None and leg['payload_event'] is not None:
                    self.delivery_event=dict(first_tick=leg['payload_event']['first_tick'],leg_id=leg['id'],facts=copy.deepcopy(facts))
                if leg['direction']=='return':
                    if self.return_event is None and leg['carrier_event'] is not None:self.return_event=copy.deepcopy(leg['carrier_event'])
                    if self.payload_return_event is None and leg['payload_event'] is not None:self.payload_return_event=copy.deepcopy(leg['payload_event'])
            if self.presence_motion is not None:
                motion=self.presence_motion;pf=self.presence_facts()
                if pf[motion['destination']]:
                    self.presence_events.append(dict(kind='presence_'+motion['destination'],first_tick=self.tick,motion=copy.deepcopy(motion),facts=pf))
                    self.presence_motion=None
            state=self.state()
            if self.trace:self.trace.write(json.dumps(state)+'\n')
            if self.step_callback is not None:
                facts=self.public_inspection_sample();result=self.step_callback(facts)
                if self.service_trace:self.service_trace.write(json.dumps(dict(facts=facts,**result))+'\n')

    def close(self):
        try:
            if self.service_trace:self.service_trace.close()
        finally:super().close()
