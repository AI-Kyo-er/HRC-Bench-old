"""从实际碰撞几何计算人可选择的柜顶放置位置，不读取任务成绩。"""
import numpy as np


def geom_vertical_half_extent(model,data,index):
    rotation=data.geom_xmat[index].reshape(3,3);size=model.geom_size[index];kind=int(model.geom_type[index])
    if kind==6:return float(np.dot(np.abs(rotation[2]),size))
    if kind==2:return float(size[0])
    if kind==4:return float(np.linalg.norm(rotation[2]*size))
    if kind in {3,5}:
        axis_z=abs(float(rotation[2,2]))
        return float(size[0]+size[1]*axis_z if kind==3 else size[0]*np.sqrt(max(0,1-axis_z**2))+size[1]*axis_z)
    raise ValueError('不支持的碰撞形状')


def cabinet_placement_targets(model,data,object_names):
    support=model.geom_name2id('wooden_cabinet_1_g9')
    center=data.geom_xpos[support].copy();top=center[2]+geom_vertical_half_extent(model,data,support)
    targets={}
    for name in object_names:
        candidates=[]
        for i in range(model.ngeom):
            if (model.geom_id2name(i) or '').startswith(name+'_') and int(model.geom_group[i])==0:
                candidates.append(float(data.geom_xpos[i][2])-geom_vertical_half_extent(model,data,i))
        if not candidates:continue
        body=model.body_name2id(name+'_main')
        offset=float(data.body_xpos[body][2])-min(candidates)
        targets[name+'_on_cabinet']=(float(center[0]),float(center[1]),float(top+offset+.002))
    return targets


def update_human_support_targets(env,regions):
    movable=[n for n in ['wine_bottle_1','cream_cheese_1','akita_black_bowl_1','plate_1'] if n in env.env.objects_dict]
    regions.update(cabinet_placement_targets(env.sim.model,env.sim.data,movable))
