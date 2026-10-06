"""原生公开目标的物理完成：放置接触/释放，或实测关节变化/稳定；不选择动作。"""
import numpy as np

from .native_placement import NativePlacementEvidence


def goal_success(record):return bool(record.get('native_physical_goal_success',record.get('released_stable_placement',False)))


class NativeJointEvidence:
    def __init__(self,spec):
        self.spec=spec;self.object_id=None;self.receiver_id=spec['receiver_id'];self.records=[];self.duration=0.;self.initial=None

    def update(self,previous,current,geometry_satisfied):
        dt=current['time_s']-previous['time_s']
        if dt<=0:raise ValueError('关节证据需要递增时间')
        names=self.spec['joint_names'];values=np.array([current['articulated_joints'][n] for n in names])
        prev=np.array([previous['articulated_joints'][n] for n in names])
        if self.initial is None:self.initial=prev.copy()
        speed=float(np.max(np.abs(values-prev))/dt);change=float(np.max(np.abs(values-self.initial)))
        eligible=bool(geometry_satisfied and change>.02 and speed<.08)
        self.duration=self.duration+dt if eligible else 0.
        done=self.duration>=.2-1e-9
        self.records.append({'time_s':current['time_s'],'native_geometry_satisfied':bool(geometry_satisfied),
            'native_physical_goal_success':bool(done),'joint_positions':values.tolist(),'joint_displacement_from_start':change,
            'joint_peak_step_speed':speed,'stable_duration_s':self.duration,
            'interpretation':'原生目标成立、关节真实变化且连续稳定；平移单位m、转动单位rad，不作为放置释放结果。'})
        return done


def create_goal_evidence(spec):
    if spec['kind'] in {'on','in'}:return NativePlacementEvidence(spec['object_id'],spec['receiver_id'],require_all_hand_release=spec.get('require_all_hand_release',False))
    return NativeJointEvidence(spec)


def fixture_joint_measurements(env):
    result={}
    for fixture in env.env.fixtures_dict.values():
        for name in fixture.joints:
            address=env.sim.model.get_joint_qpos_addr(name)
            if isinstance(address,(int,np.integer)):result[name]=float(env.sim.data.qpos[address])
    return result
