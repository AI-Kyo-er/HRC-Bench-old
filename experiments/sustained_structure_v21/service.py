"""伙伴贡献事件机，只使用本tick公开物理事实及已收到的请求。"""
import copy
import json
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name('config.json').read_text())


class InspectionService:
    def __init__(self, presence_clause, emit, start_presence):
        assert presence_clause in ('stay', 'retain', 'withdraw')
        self.presence_clause = presence_clause
        self.emit = emit
        self.start_presence = start_presence
        self.committed = False
        self.completed = False
        self.qualified_ticks = 0
        self.last_tick = None
        self.departed_once = False
        self.far_arrival_tick = None
        self.return_started = False
        self.returned = False
        self.acceptances = 0
        self.request_rejections = 0
        self.duplicate_requests = 0

    def snapshot(self):
        return copy.deepcopy({
            key: getattr(self, key) for key in (
                'committed', 'completed', 'qualified_ticks', 'last_tick',
                'departed_once', 'far_arrival_tick', 'return_started', 'returned',
                'acceptances', 'request_rejections', 'duplicate_requests')})

    @staticmethod
    def physically_available(facts):
        return facts['presence']['near'] and not facts['presence_moving']

    @staticmethod
    def blue_observable(facts):
        return facts['inspection']['satisfied'] and not facts['robot_blue_contact']

    def request(self, facts):
        tick = facts['tick']
        if self.completed:
            self.duplicate_requests += 1
            reply = dict(decision='already_completed', no_op=True,
                         content='既定检查贡献已完成，重复请求不会再启动。')
        elif self.committed:
            self.duplicate_requests += 1
            reply = dict(decision='already_committed', no_op=True,
                         content='现有检查承诺仍有效，重复请求不会清零或重启。')
        elif not self.physically_available(facts):
            self.request_rejections += 1
            reply = dict(decision='rejected', no_op=False,
                         content='当前未在近端稳定可用；拒绝且不排队。')
        elif not self.blue_observable(facts):
            self.request_rejections += 1
            reply = dict(decision='rejected', no_op=False,
                         content='blue尚未稳定支撑在检查台，或机器人仍接触blue；拒绝且不排队。')
        else:
            self.committed = True
            self.acceptances += 1
            reply = dict(decision='accepted', no_op=False,
                         content='接受局部blue检查职责；暂时保持实际检查前提，外层约定和已有工作保留。')
        self.emit(dict(kind='check_request_reply', actual_tick=tick,
                       qualified_ticks=self.qualified_ticks, **reply))
        return copy.deepcopy(reply)

    def step(self, facts):
        tick = facts['tick']
        if self.last_tick is not None and tick != self.last_tick + 1:
            raise ValueError('贡献采样必须逐tick连续，观察/重复调用不能追加进度。')
        self.last_tick = tick
        if self.departed_once and self.far_arrival_tick is None and facts['presence']['far'] and not facts['presence_moving']:
            self.far_arrival_tick = tick
            self.emit(dict(kind='presence_far_observed', actual_tick=tick,
                           content='伙伴代理已真实到达远端并稳定。'))
        if self.far_arrival_tick is not None and not self.return_started and tick - self.far_arrival_tick >= CONFIG['far_dwell_ticks']:
            motion = self.start_presence('near')
            self.return_started = True
            self.emit(dict(kind='presence_return_started', actual_tick=tick,
                           motion=motion, content='伙伴代理开始真实返回。'))
        if self.return_started and not self.returned and facts['presence']['near'] and not facts['presence_moving']:
            self.returned = True
            self.emit(dict(kind='presence_near_observed', actual_tick=tick,
                           content='伙伴代理已真实返近并稳定；被撤销职责不会自动重接。'))
        qualified = self.committed and not self.completed and self.physically_available(facts) and self.blue_observable(facts)
        if qualified:
            self.qualified_ticks += 1
        if qualified and self.presence_clause != 'stay' and not self.departed_once and self.qualified_ticks == CONFIG['leave_after_qualified_ticks']:
            self.departed_once = True
            motion = self.start_presence('far')
            if self.presence_clause == 'withdraw':
                self.committed = False
                kind = 'check_commitment_withdrawn'
                content = '公开撤销当前检查承诺，已检查记录保留；返回后需重新请求。'
            else:
                kind = 'check_commitment_suspended'
                content = '真实离开期间暂停当前检查贡献，承诺与已有检查记录保留；返近可继续。'
            self.emit(dict(kind=kind, actual_tick=tick,
                           qualified_ticks=self.qualified_ticks, motion=motion, content=content))
        if self.committed and self.qualified_ticks == CONFIG['inspection_required_ticks'] and not self.completed:
            self.completed = True
            self.committed = False
            self.emit(dict(kind='partner_check_handoff', actual_tick=tick,
                           qualified_ticks=self.qualified_ticks,
                           content='实际检查贡献已完成，现在交还blue，按当前有效外层约定继续；其余已实现工作保留。'))
        return dict(sample_qualified=bool(qualified), service=self.snapshot())
