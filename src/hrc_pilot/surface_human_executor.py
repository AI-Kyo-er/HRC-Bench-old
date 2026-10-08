"""执行模型已选的桌面放置；实际物品高度与公开表面坐标分开，不路由任务策略。"""
from collections.abc import Mapping

from .activity_workspace import body_target_on_surface
from .contract_human_executor import ContractHumanExecutor


class SurfaceDestinations(Mapping):
    """仅供当前运动宏查询的目标视图；公共区域字典始终保存表面位置。"""
    def __init__(self,actor,public_regions,surface_names):
        self.actor=actor;self.public_regions=public_regions;self.surface_names=set(surface_names)
        if not self.surface_names.issubset(public_regions):raise ValueError('桌面目标必须有公开表面坐标')

    def __iter__(self):return iter(self.public_regions)
    def __len__(self):return len(self.public_regions)

    def __getitem__(self,name):
        point=self.public_regions[name]
        if name not in self.surface_names:return point
        actor=self.actor;choice=getattr(actor,'_table_input_choice',None)
        if choice is not None:
            obj=choice.get('object_id') or (actor.held if choice['action']=='place' else None)
            if actor.held and actor.held!=obj and name==actor.held+'_personal' and actor.auto_buffer:
                obj=actor.held
        elif actor.phase=='buffer_owned_object':obj=actor.held
        else:obj=actor.object_id
        if obj is None:return point
        return body_target_on_surface(actor.env.sim.model,actor.env.sim.data,obj,point)


class SurfaceHumanExecutor(ContractHumanExecutor):
    def __init__(self,env,regions,**kwargs):
        surfaces=getattr(env.env,'_hrc_table_surface_positions',None)
        if surfaces is None:raise ValueError('桌面执行器需要明确注册的表面坐标')
        super().__init__(env,regions,**kwargs)
        self.regions=SurfaceDestinations(self,regions,surfaces)
        self._table_input_choice=None

    def accept_choice(self,choice,request_id):
        if request_id==self.last_request:return
        self._table_input_choice=choice
        try:
            # 继承已有单手、原持物暂放、真实Robot接触及幂等运动契约。
            super().accept_choice(choice,request_id)
            if self.receipts and self.receipts[-1]['request_id']==request_id and self.receipts[-1]['accepted']:
                destination=choice.get('destination')
                if destination in self.regions.surface_names and choice['action'] in {'place','relocate'}:
                    obj=choice.get('object_id') or self.held
                    self.receipts[-1]['table_surface_placement']={
                        'object_id':obj,'destination':destination,
                        'surface_xyz':list(self.regions.public_regions[destination]),
                        'resolved_object_body_xyz':body_target_on_surface(self.env.sim.model,self.env.sim.data,obj,
                            self.regions.public_regions[destination]),
                        'scope':'已选放置的几何参数；接受不是完成，不生成下一贡献。'}
        finally:self._table_input_choice=None
