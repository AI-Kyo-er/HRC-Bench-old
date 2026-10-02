"""只增加伙伴可用性时钟；原v8动力学、simulate和profile原样继承。"""
from experiments.physical.world import DT
from experiments.structure_v8.world_v2 import TransportWorld,CONFIG,CONFIG_PATH,profile_distance

BUSY_SECONDS=8.0
BUSY_TICKS=1920
assert BUSY_TICKS*DT==BUSY_SECONDS


class ResponsiveWorld(TransportWorld):
    def __init__(self,seed=0,initial_availability='ready',**kwargs):
        assert initial_availability in ('ready','temporarily_busy')
        self.initial_availability=initial_availability
        self.common_start_tick=None
        super().__init__(seed=seed,**kwargs)
        self.common_start_tick=self.tick
        self.initial_state=self.state()

    def availability(self):
        if self.common_start_tick is None:
            return dict(status=self.initial_availability,common_start_tick=None,physics_tick=self.tick,elapsed_seconds=None,ready_event=None)
        ready_tick=self.common_start_tick+(BUSY_TICKS if self.initial_availability=='temporarily_busy' else 0)
        ready=self.tick>=ready_tick
        return dict(status='ready' if ready else 'temporarily_busy',common_start_tick=self.common_start_tick,physics_tick=self.tick,
            elapsed_seconds=(self.tick-self.common_start_tick)*DT,
            ready_event=dict(kind='partner_ready',availability_actual_tick=ready_tick,content='伙伴资源现在可接受新的运输请求；不会自动执行此前拒绝的请求。') if ready else None)

    def state(self):
        state=super().state()
        # 无缓存、无副作用：基类simulate每tick记录当前同tick时钟事实。
        state['availability']=self.availability()
        return state

    def wait_ready(self):
        before=self.tick;self.phase='wait_ready'
        for _ in range(CONFIG['wait_budget_ticks']):
            if self.availability()['status']=='ready':break
            self.simulate(1)
        return dict(success=self.availability()['status']=='ready',ticks=self.tick-before,kind='ready',transport_started=self.delivery_start_tick is not None)
