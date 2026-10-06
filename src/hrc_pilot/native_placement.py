"""放置的接触、释放与稳定证据；不向控制器发送动作。"""
import numpy as np


class NativePlacementEvidence:
    def __init__(self, object_id, receiver_id, stable_seconds=.2):
        self.object_id=object_id;self.receiver_id=receiver_id
        self.stable_seconds=stable_seconds;self.duration=0.;self.records=[]

    def update(self, previous, current, geometry_satisfied):
        dt=current['time_s']-previous['time_s']
        if dt<=0:raise ValueError('物理完成证据需要递增时间')
        speed=float(np.linalg.norm(np.asarray(current['objects'][self.object_id])-previous['objects'][self.object_id])/dt)
        receiver_speed=float(np.linalg.norm(np.asarray(current['objects'][self.receiver_id])-previous['objects'][self.receiver_id])/dt)
        supported=False;gripper_contact=False
        for pair in current['contacts']:
            a,b=pair['geom1'] or '',pair['geom2'] or ''
            if b.startswith(self.object_id+'_'):a,b=b,a
            if a.startswith(self.object_id+'_'):
                supported|=b.startswith(self.receiver_id+'_')
                gripper_contact|=b.startswith('gripper')
        aperture=sum(abs(value) for value in current['robot_qpos'][-2:])
        released=not gripper_contact and aperture>=.04
        eligible=bool(geometry_satisfied and supported and released and speed<.08 and receiver_speed<.08)
        self.duration=self.duration+dt if eligible else 0.
        completed=self.duration>=self.stable_seconds-1e-9
        self.records.append({'time_s':current['time_s'],'native_geometry_satisfied':bool(geometry_satisfied),
                             'receiver_contact':bool(supported),'gripper_contact':bool(gripper_contact),
                             'gripper_aperture_m':float(aperture),'released':bool(released),
                             'object_speed_m_s':speed,'receiver_speed_m_s':receiver_speed,
                             'stable_duration_s':self.duration,'released_stable_placement':completed})
        return completed
