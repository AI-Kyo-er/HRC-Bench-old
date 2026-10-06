"""原生场景的可见运动反馈与事后互动测量，不选择任何控制动作。"""
import numpy as np


class NativeMotionObserver:
    def __init__(self):
        self.previous=None
        self.initial_objects=None

    def update(self, record):
        if self.initial_objects is None:self.initial_objects=record['objects']
        previous=self.previous
        dt=record['time_s']-previous['time_s'] if previous is not None else 0.
        speed=(float(np.linalg.norm(np.asarray(record['robot_ee'])-previous['robot_ee'])/dt)
               if dt>0 else 0.)
        result={'eef_xyz':record['robot_ee'],'eef_speed_m_s':speed,
                'gripper_joint_positions':record['robot_qpos'][-2:],
                'object_height_change_from_first_observation_m':{
                    name:float(position[2]-self.initial_objects[name][2])
                    for name,position in record['objects'].items()},
                'source':'current_and_previous_public_geometry','motion_observed':speed>.015}
        self.previous=record
        return result


def interaction_metrics(trace, human_control, human_decisions):
    """时长、空间、实际动作与等待测量；不合成未经验证的cobalance分数。"""
    if len(trace)<2:return {}
    robot_time=human_time=concurrent_time=stationary_time=0.
    distances=[]
    for first,second in zip(trace,trace[1:]):
        dt=second['time_s']-first['time_s']
        robot=np.linalg.norm(np.asarray(second['robot_ee'])-first['robot_ee'])/dt>.015
        human=(np.linalg.norm(np.asarray(second['human_hand_position'])-first['human_hand_position'])/dt>.015
               or np.linalg.norm(np.asarray(second['human_position'])-first['human_position'])/dt>.015)
        robot_time+=dt*robot;human_time+=dt*human;concurrent_time+=dt*(robot and human)
        stationary_time+=dt*(not robot and not human)
        distances.append(float(np.linalg.norm(np.asarray(first['robot_ee'])-first['human_hand_position'])))
    observe_time=0.
    for index,row in enumerate(human_decisions):
        end=human_decisions[index+1]['time_s'] if index+1<len(human_decisions) else trace[-1]['time_s']
        if row['parsed_decision']['intent']=='observe':observe_time+=end-row['time_s']
    return {'robot_ee_motion_time_s':float(robot_time),'human_motion_time_s':float(human_time),
            'simultaneous_motion_time_s':float(concurrent_time),'both_stationary_time_s':float(stationary_time),
            'human_observe_command_time_s':float(observe_time),
            'minimum_ee_fingertip_distance_m':min(distances),
            'human_force_contact_samples':sum(bool(row['contact_geoms']) for row in human_control),
            'interpretation':'实际运动与等待描述；距离不是碰撞证明，指尖代理与EE距离不是完整人体安全指标。'}
