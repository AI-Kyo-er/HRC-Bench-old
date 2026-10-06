"""从原生任务与场景库存构建可复现案例，不规定人的动作序列。"""
from dataclasses import asdict,dataclass

import numpy as np


@dataclass(frozen=True)
class NativeSceneCase:
    key: str
    task_id: int
    label: str
    focus: str
    suite: str = 'libero_goal'
    preferred_personal_objects: tuple[str,...] = ()


CASES={c.key:c for c in [
    NativeSceneCase('food_into_bowl',6,'奶酪包入碗','小包装/接收容器，可发生人移动容器或整理另一物品的干预',preferred_personal_objects=('akita_black_bowl_1','wine_bottle_1')),
    NativeSceneCase('bottle_on_rack',9,'酒瓶放酒架','细长瓶子/指定架面，人可维护附近个人取用区域',preferred_personal_objects=('cream_cheese_1','plate_1')),
    NativeSceneCase('bowl_on_stove',1,'碗放炉面','锅具/固定炉面，共享台面占用与相邻整理',preferred_personal_objects=('plate_1','cream_cheese_1')),
    NativeSceneCase('drawer_access',0,'打开中层抽屉','关节开合/空间接近，人可自行整理物品或协商访问',preferred_personal_objects=('wine_bottle_1','plate_1'))
]}


def resolve_goal(env):
    goals=env.env.parsed_problem['goal_state']
    if len(goals)!=1:raise ValueError('当前通用原生入口要求单个公开目标，复合目标需独立定义物理证据')
    goal=goals[0];kind=goal[0].lower()
    if kind in {'on','in'} and len(goal)==3:
        obj,receiver=goal[1:]
        if receiver not in env.env.obj_body_id:
            if receiver not in env.env.object_sites_dict:raise ValueError('目标接收区域没有原生site对应')
            receiver=env.env.object_sites_dict[receiver].parent_name
        if obj not in env.env.obj_body_id or receiver not in env.env.obj_body_id:raise ValueError('公开目标实体缺少物理body')
        return {'kind':kind,'object_id':obj,'receiver_id':receiver,'native_target_symbol':goal[2],'require_all_hand_release':True,'require_robot_open_aperture':False}
    if kind in {'open','close','turnon','turnoff'} and len(goal)==2:
        symbol=goal[1]
        if symbol in env.env.object_sites_dict:
            site=env.env.object_sites_dict[symbol];parent=site.parent_name;joints=list(site.joints)
        else:parent=symbol;joints=list(env.env.get_object(symbol).joints)
        if not joints:raise ValueError('关节目标没有可验证的原生关节')
        return {'kind':kind,'object_id':None,'receiver_id':parent,'native_target_symbol':symbol,'joint_names':joints}
    raise ValueError(f'尚未实现这一公开目标的物理判据：{goal}')


def scene_regions(objects,movable_names):
    """公开个人整理位置只依赖初始化库存和布局，不读取评分或人模型计划。"""
    names=sorted(name for name in movable_names if name in objects)
    if not names:raise ValueError('场景没有可操作库存')
    regions={}
    for index,name in enumerate(names):
        home=np.asarray(objects[name],dtype=float)
        regions[name+'_home']=tuple(home)
        # Separate near-edge places for tabletop inventory; preserve support height.
        regions[name+'_personal']=(float(-.15+.12*index),.44,float(home[2]))
    regions['near_human']=regions[names[0]+'_personal']
    return regions


def case_metadata(key):return asdict(CASES[key])
