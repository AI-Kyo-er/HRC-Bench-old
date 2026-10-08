"""基于碰撞支撑面的关系放置；资产声明能力，几何解算不选择人贡献。"""
import numpy as np

from .human_support_targets import geom_vertical_half_extent


# 资产的物理用途声明，不是任务分工或所需下一动作。
RELATION_AFFORDANCES={'akita_black_bowl_1':('in',),'plate_1':('on',)}


def collision_geoms(model,name):
    return [i for i in range(model.ngeom) if (model.geom_id2name(i) or '').startswith(name+'_')
            and int(model.geom_group[i])==0 and (model.geom_contype[i] or model.geom_conaffinity[i])]


def central_support_surface(model,data,name):
    """找穿过物体中心竖线的水平碰撞盒，排除碗侧壁和视觉mesh。"""
    body=model.body_name2id(name+'_main');origin=data.body_xpos[body]
    if data.body_xmat[body].reshape(3,3)[2,2]<.95:return None
    candidates=[]
    for i in collision_geoms(model,name):
        if int(model.geom_type[i])!=6:continue
        rotation=data.geom_xmat[i].reshape(3,3);axis=int(np.argmax(np.abs(rotation[2])))
        if abs(rotation[2,axis])<.98:continue
        size=model.geom_size[i]
        if size[axis]>.012:continue
        local=rotation.T@(origin-data.geom_xpos[i])
        lateral=[j for j in range(3) if j!=axis]
        if any(abs(local[j])>size[j]-.001 for j in lateral):continue
        top=float(data.geom_xpos[i][2])+geom_vertical_half_extent(model,data,i)
        candidates.append((top,i))
    if not candidates:return None
    top,index=max(candidates)
    return {'xyz':[float(origin[0]),float(origin[1]),top],
            'collision_geom':model.geom_id2name(index)}


def relation_placement_targets(model,data,object_names,affordances=RELATION_AFFORDANCES):
    targets={}
    for reference,relations in affordances.items():
        if reference not in object_names:continue
        surface=central_support_surface(model,data,reference)
        if surface is None:continue
        for obj in object_names:
            if obj==reference:continue
            body=model.body_name2id(obj+'_main')
            joint=int(model.body_jntadr[body])
            if joint<0 or int(model.jnt_type[joint])!=0:continue
            geoms=collision_geoms(model,obj)
            if not geoms:continue
            bottom=min(float(data.geom_xpos[i][2])-geom_vertical_half_extent(model,data,i) for i in geoms)
            bottom_offset=float(data.body_xpos[body][2])-bottom
            for relation in relations:
                name=f'{obj}__{relation}__{reference}'
                point=np.asarray(surface['xyz'])+[0,0,bottom_offset+.004]
                targets[name]={'object_id':obj,'relation':relation,'reference_object_id':reference,
                    'target_xyz':point.tolist(),'support_collision_geom':surface['collision_geom'],
                    'source':'current_collision_support_not_task_score',
                    'interpretation':'已选物品按当前朝向连续搬运到参考物支撑面；放下后由原生接触沉降，不保证容器包含或任务完成。'}
    return targets


def update_human_relation_targets(env,regions):
    names=list(env.env.obj_body_id)
    targets=relation_placement_targets(env.sim.model,env.sim.data,names)
    # 不可解算时保留已选目标的标识并标记不可达，不能继续沿用旧坐标执行。
    previous=getattr(env.env,'_hrc_relation_targets',{})
    accessibility=getattr(env.env,'_hrc_region_accessibility',{})
    for name in set(previous)|set(targets):accessibility[name]=name in targets
    regions.update({name:tuple(value['target_xyz']) for name,value in targets.items()})
    env.env._hrc_relation_targets=targets
    env.env._hrc_region_accessibility=accessibility
    return targets
