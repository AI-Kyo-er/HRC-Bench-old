"""分离日常操作、暂放与交付位置；由实际碰撞面解算，不选择双方任务策略。"""
from copy import deepcopy

import numpy as np

from .human_relation_targets import collision_geoms


# 相对桌面中心的局部XY位置。命名是用途声明，非动作队列或已接受分工。
TABLE_ZONES={
    'serving_ready':(.16,.04),
    'snack_delivery':(.28,.45),
    'drink_staging':(.02,.45),
    'akita_black_bowl_1_personal':(.35,.24),
    'wine_bottle_1_personal':(-.20,-.02),
    'plate_1_personal':(-.18,.45),
    'cream_cheese_1_personal':(.0,.24),
}


def object_collision_bounds(model,data,name):
    ids=collision_geoms(model,name)
    if not ids:raise ValueError('物品没有可测碰撞几何：'+name)
    lower=[];upper=[]
    for index in ids:
        if int(model.geom_type[index])!=6:raise ValueError('当前桌面布局资格检查只支持已测量的碰撞盒')
        extent=np.abs(data.geom_xmat[index].reshape(3,3))@model.geom_size[index]
        lower.append(data.geom_xpos[index]-extent);upper.append(data.geom_xpos[index]+extent)
    return np.min(lower,axis=0),np.max(upper,axis=0)


def make_table_workspace(model,data,movable_names,fixture_names=(),*,zones=None,clearance_m=.025):
    """保守验证静态桌面位置；不保证运动路径、机器人可达性或活动成功。"""
    if not movable_names:raise ValueError('布局需要实际可移动物品')
    if len(set(movable_names))!=len(movable_names):raise ValueError('可移动物品标识重复')
    if not np.isfinite(clearance_m) or clearance_m<0:raise ValueError('布局间距必须非负且有限')
    support=model.geom_name2id('table_collision')
    if int(model.geom_type[support])!=6:raise ValueError('桌面必须是可测碰撞盒')
    rotation=data.geom_xmat[support].reshape(3,3);center=data.geom_xpos[support]
    if np.max(np.abs(rotation[2]-[0,0,1]))>1e-6:
        raise ValueError('当前布局只支持水平桌面')
    top=float(center[2]+model.geom_size[support][2])
    objects={}
    maximum=np.zeros(2)
    for name in movable_names:
        lower,upper=object_collision_bounds(model,data,name)
        origin=data.body_xpos[model.body_name2id(name+'_main')]
        half=np.maximum(origin-lower,upper-origin)[:2]
        objects[name]={'bottom_offset_m':float(origin[2]-lower[2]),'xy_half_extent_m':half.tolist()}
        maximum=np.maximum(maximum,half)
    fixtures={name:object_collision_bounds(model,data,name) for name in fixture_names}
    chosen=deepcopy(TABLE_ZONES if zones is None else zones)
    positions={};targets={}
    # 用最大物品的当前轴对齐包围盒验证所有区，不限制其用途或替模型选空区。
    local_half=np.abs(rotation[:2,:2]).T@maximum
    for name,value in chosen.items():
        xy=np.asarray(value,dtype=float)
        if xy.shape!=(2,) or not np.isfinite(xy).all():raise ValueError('区域XY须是有限二维坐标')
        if np.any(np.abs(xy)+local_half+clearance_m>model.geom_size[support][:2]):
            raise ValueError('功能区过近桌边：'+name)
        point=center[:2]+rotation[:2,:2]@xy
        for fixture,(lower,upper) in fixtures.items():
            if np.all(point+maximum+clearance_m>lower[:2]) and np.all(point-maximum-clearance_m<upper[:2]):
                raise ValueError('功能区与固定物件重叠：'+name+' / '+fixture)
        for other,old in positions.items():
            if np.all(np.abs(point-np.asarray(old)[:2])<2*maximum+clearance_m):
                raise ValueError('不同功能区的物品占用空间重叠：'+name+' / '+other)
        positions[name]=[float(point[0]),float(point[1]),top]
        targets[name]={}
        for obj,shape in objects.items():
            target=np.r_[point,top+shape['bottom_offset_m']+.002]
            hand=target+[0,0,.06]
            if np.any(hand<[-.7,-.4,.95]) or np.any(hand>[.7,.9,1.5]):
                raise ValueError('放置接近点超出已声明人工作区：'+name+' / '+obj)
            targets[name][obj]=target.tolist()
    return {'source':'measured_table_and_object_collision_geometry','table_surface_z_m':top,
        'zone_surface_positions':positions,'object_specific_body_targets':targets,
        'object_shapes':objects,'clearance_m':clearance_m,
        'scope':'水平桌面上的分离功能区与当前朝向的对象放置中心。未验证移动物品占用、实际运动路径、机器人可达性、接管或完整任务；不选择下一贡献。'}
