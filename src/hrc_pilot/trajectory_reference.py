"""已有成功轨迹的闭环位姿跟随，仅用于参考，不是被测模型策略。"""
import numpy as np
from scipy.spatial.transform import Rotation


class TrajectoryReference:
    def __init__(self,trace,actions):
        self.trace=trace;self.actions=np.asarray(actions,dtype=float);self.cursor=0;self.records=[]
        assert len(trace)==len(actions)+1

    def next_action(self,state):
        state=np.asarray(state,dtype=float)
        index=min(self.cursor,len(self.actions)-1);target=self.trace[index+1]
        error=np.asarray(target['robot_ee'])-state[:3]
        rotation=Rotation.from_quat(target['eef_quaternion_xyzw'])*Rotation.from_rotvec(state[3:6]).inv()
        angular=rotation.as_rotvec()
        action=np.r_[np.clip(error/.05,-.2,.2),np.clip(angular/.5,-.1,.1),self.actions[index,-1]]
        if np.linalg.norm(error)<.006 and np.linalg.norm(angular)<.12 and self.cursor<len(self.actions)-1:
            self.cursor+=1
        self.records.append({'source_index':index,'target_eef_xyz':target['robot_ee'],
            'target_quaternion_xyzw':target['eef_quaternion_xyzw'],'position_error_m':float(np.linalg.norm(error)),
            'rotation_error_rad':float(np.linalg.norm(angular)),'action':action.tolist()})
        return action[None]
