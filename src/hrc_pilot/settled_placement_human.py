"""已选放置的低层幂等执行：接触支撑后的重力沉降不触发重复抓取。"""
import numpy as np

from .kinematic_human import KinematicHuman


class SettledPlacementHuman(KinematicHuman):
    def accept_choice(self,choice,request_id):
        obj=choice.get('object_id');dest=choice.get('destination')
        eligible=(request_id!=self.last_request and choice['action']=='relocate' and self.held is None
                  and self.phase=='idle' and obj in self.object_q and dest in self.regions
                  and getattr(self.env.env,'_hrc_region_accessibility',{}).get(dest,True))
        if eligible:
            delta=self.object_position(obj)-np.asarray(self.regions[dest]);_,velocity_index=self.object_q[obj]
            slow=np.linalg.norm(self.env.sim.data.qvel[velocity_index:velocity_index+3])<.02
            supported=False;robot_contact=False
            for i in range(self.env.sim.data.ncon):
                contact=self.env.sim.data.contact[i]
                names=[self.env.sim.model.geom_id2name(g) or '' for g in [contact.geom1,contact.geom2]]
                if any(n.startswith(obj+'_') for n in names):
                    supported|=any(not n.startswith(('robot','gripper','human',obj+'_')) for n in names)
                    robot_contact|=any(n.startswith(('robot','gripper')) for n in names)
            if slow and supported and not robot_contact and np.linalg.norm(delta[:2])<.01 and abs(delta[2])<.025:
                self.last_request=request_id;self.accepted_intent='relocate';self.active_request=request_id
                self.object_id=obj;self.destination=dest;self.transfer_destination=dest
                self.receipts.append({'physics_time_s':float(self.env.sim.data.time),'request_id':request_id,
                    'choice':choice,'accepted':True,'error':None,'effect':'already_at_requested_supported_position',
                    'placement_tolerance_m':{'xy':.01,'z':.025},'placement_linear_speed_limit_m_s':.02})
                if choice.get('presence_choice')=='return_to_work' and np.linalg.norm(self.body_base-np.array([.25,.60]))>.004:
                    # 兑现模型明确选择的返回，不把已在目标的物品当作身体已返回。
                    self.body_target=np.array([.25,.60]);self.target=np.r_[self.body_target,1.12];self.phase='return'
                    self.receipts[-1]['effect']='placement_satisfied_explicit_return_in_progress'
                else:self.target=self.position().copy();self._complete()
                return
        super().accept_choice(choice,request_id)
