"""重建MuJoCo实际缓存几何帧；用独立物体位置检验，不拟合任务目标。"""
import mujoco
import numpy as np


def replay_recorded_geometry(model,data,record,position_tolerance_m=1e-6):
    qpos=np.asarray(record['qpos'],dtype=float);qvel=np.asarray(record['qvel'],dtype=float)
    bodies={name:mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,name+'_main') for name in record['objects']}
    if any(index<0 for index in bodies.values()):raise ValueError('轨迹对象缺少对应物理body')
    candidates=[]
    if int(model.opt.integrator)==0:
        # mj_step的Euler积分最后更新qpos，而xpos/xmat仍对应积分前的位置。
        previous=qpos.copy();mujoco.mj_integratePos(model,previous,qvel,-float(model.opt.timestep))
        candidates.append(('cached_before_euler_position_integration',previous,-float(model.opt.timestep)))
    candidates.append(('forwarded_recorded_qpos',qpos,0.))
    errors={}
    selected=None
    for name,positions,offset in candidates:
        data.qpos[:]=positions;data.qvel[:]=qvel;mujoco.mj_forward(model,data)
        error=max(float(np.max(np.abs(data.xpos[index]-record['objects'][obj]))) for obj,index in bodies.items())
        errors[name]=error
        if selected is None and error<=position_tolerance_m:selected=(name,positions,offset,error)
    if selected is None:raise ValueError('物理帧不能与记录的物体位置独立对齐：'+str(errors))
    name,positions,offset,error=selected
    data.qpos[:]=positions;data.qvel[:]=qvel;mujoco.mj_forward(model,data)
    return {'frame':name,'physics_offset_s':offset,'body_position_max_axis_error_m':error,
            'body_position_tolerance_m':position_tolerance_m,'candidate_body_errors_m':errors}
