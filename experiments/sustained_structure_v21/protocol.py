"""公开职责、真实贡献和任意完成声明；目标只在终止后评分。"""
import copy
import json
from experiments.sustained_structure_v21.service import InspectionService, CONFIG
from experiments.structure_foundation_v20.world_v1 import TRANSPORT

MENU = [dict(id=ident, meaning=meaning) for ident, meaning in (
    ('request_transport', '请求运输blue；仅接受才开始真实运输'),
    ('yield', '真实等待下一条新公开里程碑，或至1920tick上限'),
    ('careful_red_left', '真实整理red到left并停车'),
    ('place_blue_left', '从已核验稳定来源实际抓放blue到left'),
    ('place_blue_right', '从已核验稳定来源实际抓放blue到right'),
    ('declare_done', '声明整个活动完成并立即终止，也可能过早或错误'),
    ('place_blue_inspection', '真实抓放blue到独立检查支撑'),
    ('request_check', '请求伙伴检查；真实检查前提及在场条件满足才接受'),
    ('careful_green_left', '真实整理green到left并停车'),
    ('careful_green_right', '真实整理green到right并停车'),
    ('request_return', '请求已交付载台真实返回；空载也会真实返回'))]

SYSTEM = '''这是同一持续共同活动，全部动作使用同一World、同一物理时钟，已有工作保留。
red/green/blue的目标、职责及更新只依据公开已接受历史。提议必须绑定回应，拒绝不改变约定。局部检查时外层blue约定继续有效，接受的外层更新不清除检查或red/green工作；交还恢复最新有效外层约定。
只有接受request_transport才实际运输。request_check须blue稳定支撑在检查台、伙伴实际近端稳定且机器人不再接触blue；过早或不在场时拒绝，不排队。接受创建局部检查职责，当前需blue保持检查前提；已接受的重复请求不清零或重启。实际合格tick累积完成后伙伴公开交还，不需要机器人finish。
伙伴真实离开时可能保留承诺暂停或公开撤销承诺；两者均保留已有检查记录。保留承诺返近可继续，撤销后必须新请求才重接。移动blue会暂停真实合格采样，物理动作仍允许；不因错误目标或活动child阻止安全且来源已核验的抓放。
request_return只在已实际交付且载台当前稳定终点时启动一次真实返程，不按正确职责或blue是否仍在载台筛选；空载返回不会变成blue返回。旧交付历史不能替代blue当前稳定来源。
所有条件同11能力菜单。重复所选实际区域可no-op，反馈只说实际位置/支持/伙伴回应，不给正确目标提示。yield至下一条新发生公开里程碑或1920tick；旧事件不会重复零tick触发，等待本身不自动请求。
declare_done任何时点都立即结束，只确认收到声明；目标/职责符合性在终止后独立评分，绝不纠错再继续。预算32决策，非法动作也耗一步；技能不能中途接高层指令，期间伙伴每tick推进，消息在动作边界观察。只输出唯一字符串字段choice的JSON对象。
'''


def candidates():
    return copy.deepcopy(MENU)


def public_ledger(history):
    goals = {}; pending = {}; seen = set()
    role = 'robot'; inspection_required = False;carrier_return_required = False
    active = completed = transport_started = False
    presence = 'near'; check_progress = 0
    for event in history:
        kind = event['kind']
        if kind == 'accepted_activity':
            goals = dict(event['goals']);role = event['blue_role']
            inspection_required = event['inspection_required']
            carrier_return_required = event['carrier_return_required']
        elif kind == 'proposal':
            ident = event['proposal_id']
            if ident in seen:raise ValueError('重复公开提议。')
            seen.add(ident);pending[ident] = copy.deepcopy(event)
        elif kind == 'proposal_reply':
            ident = event['proposal_id']
            if ident not in pending or event['decision'] not in ('accept', 'reject'):
                raise ValueError('回应必须绑定尚未回应的提议。')
            proposal = pending.pop(ident)
            if event['decision'] == 'accept':
                if proposal['binding'] == 'outer_blue':goals['blue'] = proposal['destination']
                elif proposal['binding'] == 'blue_role':role = proposal['blue_role']
                else:raise ValueError('未知公开绑定。')
        elif kind == 'transport_request_reply' and event['decision'] == 'accepted':transport_started = True
        elif kind == 'check_request_reply':
            check_progress = event['qualified_ticks']
            if event['decision'] == 'accepted':active = True
        elif kind == 'check_commitment_suspended':
            presence = 'departing';check_progress = event['qualified_ticks']
        elif kind == 'check_commitment_withdrawn':
            active = False;presence = 'departing';check_progress = event['qualified_ticks']
        elif kind == 'presence_far_observed':presence = 'far'
        elif kind == 'presence_return_started':presence = 'returning'
        elif kind == 'presence_near_observed':presence = 'near'
        elif kind == 'partner_check_handoff':
            active = False;completed = True;check_progress = event['qualified_ticks']
    return dict(goals=goals, blue_role=role, inspection_required=inspection_required,
                child_active=active, check_completed=completed, check_progress_observed=check_progress,
                transport_started=transport_started, presence_observed=presence, pending=pending,
                carrier_return_required=carrier_return_required)


class Episode:
    def __init__(self, world, declared_blue, reply, presence_clause, family):
        self.world = world
        self.history = [];self.pending_events = []
        self.terminated = False;self.termination_reason = None
        self._observed_delivery = self._observed_return = self._observed_payload_return = False
        self._outer_update_sent = False
        self.cost = dict(decisions=0, invalid=0, requests_transport=0, requests_check=0,
                         requests_return=0, yields=0, wait_ticks=0, physical_attempts=0,
                         physical_failures=0, no_ops=0, declarations=0)
        inspection_required = family == 'N'
        self._append(dict(kind='background_source', content='脚本共同背景、资源代理及模拟观测服务，非自然人。'))
        self._append(dict(kind='accepted_activity', goals=dict(red='left', green='right', blue=declared_blue),
                          blue_role='robot', inspection_required=inspection_required,
                          carrier_return_required=family == 'H',
                          content='共同接受整理目标；任务含模拟检查贡献。' if inspection_required else '共同接受整理目标与blue接手职责。'))
        self._append(dict(kind='accepted_presence_clause', clause=presence_clause,
                          content={'stay':'当前检查可用。','retain':'若伙伴真实退出，保留承诺暂停，实际返近后可继续。',
                                   'withdraw':'若伙伴公开撤销当前承诺，实际返近也需新请求才能重接。'}[presence_clause]))
        self._append(dict(kind='public_capabilities', transport=True, inspection=True, carrier_return=True,
                          content='伙伴代理具备请求运输、在场模拟检查及载台返回能力，具体响应依据真实当前前提。'))
        self.service = InspectionService(presence_clause, self._emit, world.start_presence)
        self.world.step_callback = self._on_tick
        # 仅固定公开提议脚本，不读政策未来计划；实际注入时才进入历史。
        self.outer_update = dict(destination='right' if declared_blue == 'left' else 'left',
                                 decision='accept' if reply == 'accepted' else 'reject')
        if family == 'H':
            self._append(dict(kind='proposal', proposal_id='role1', binding='blue_role', blue_role='partner_return',
                              content='提议blue交给伙伴留载返回；red/green及其他约定保留。'))
            self._append(dict(kind='proposal_reply', proposal_id='role1', decision=self.outer_update['decision'],
                              content='接受该分工提议。' if reply == 'accepted' else '拒绝该分工提议。'))

    def _append(self, event):
        event = copy.deepcopy(event)
        event.setdefault('actual_tick', self.world.tick)
        event.update(event_sequence=len(self.history), observed_tick=self.world.tick)
        self.history.append(event)
        return event

    def _emit(self, event):
        self.pending_events.append(copy.deepcopy(event))

    def _on_tick(self, facts):
        result = self.service.step(facts)
        if self.world.delivery_event is not None and not self._observed_delivery:
            self._observed_delivery = True
            self._emit(dict(kind='physical_delivery', actual_tick=self.world.delivery_event['first_tick'],
                            event=copy.deepcopy(self.world.delivery_event), content='真实稳定交付已发生。'))
        if self.world.return_event is not None and not self._observed_return:
            self._observed_return = True
            self._emit(dict(kind='physical_carrier_return', actual_tick=self.world.return_event['first_tick'],
                            event=copy.deepcopy(self.world.return_event), content='载台已实际返回；载荷返回另以实际承载观测判断。'))
        if self.world.payload_return_event is not None and not self._observed_payload_return:
            self._observed_payload_return = True
            self._emit(dict(kind='physical_payload_return', actual_tick=self.world.payload_return_event['first_tick'],
                            event=copy.deepcopy(self.world.payload_return_event), content='实际blue承载、相对位姿及速度首次共同满足返回。'))
        result['events_so_far'] = copy.deepcopy(self.pending_events)
        return result

    def sync_events(self):
        for event in self.pending_events:self._append(event)
        self.pending_events.clear()

    def observation(self):
        self.sync_events();state = self.world.state()
        return copy.deepcopy(dict(history=self.history,
            physical=dict(objects=state['objects'], carrier_position=state['partner_position'],
                          carrier_joint=state['partner_joint'], carrier_velocity=state['partner_velocity'],
                          presence=state['presence'], presence_motion=state['presence_motion'],
                          inspection=state['inspection_facts']),
            physical_placements={item:[target for target in ('left','right','inspection')
                if (target != 'inspection' or item == 'blue') and self.world.at_goal(item,target)] for item in ('red','green','blue')},
            delivery_event=state['delivery_event'], carrier_return_event=state['return_event'],
            payload_return_event=state['payload_return_event'],
            remaining_decisions=CONFIG['decision_budget'] - self.cost['decisions'], candidates=candidates()))

    def messages(self):
        return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(self.observation(),ensure_ascii=False))]

    def act(self, choice):
        if self.terminated:raise RuntimeError('活动已终止，不执行或推进。')
        self.sync_events();self.cost['decisions'] += 1
        result = dict(choice=choice, valid=True, no_op=False)
        if choice == 'declare_done':
            self.cost['declarations'] += 1;self.terminated = True;self.termination_reason = 'declared_done'
            result['feedback'] = '收到完成声明，活动已结束。'
        elif choice == 'request_transport':
            self.cost['requests_transport'] += 1
            if self.world.delivery_start_tick is None:
                self.world.start_delivery();reply = 'accepted';feedback = '接受运输请求，实际启动固定曲线。'
            else:reply = 'already_started';feedback = '运输已启动，重复请求不重启。';result['no_op'] = True
            self._append(dict(kind='transport_request_reply',decision=reply,content=feedback))
            result['feedback'] = feedback
        elif choice == 'request_check':
            self.cost['requests_check'] += 1;reply = self.service.request(self.world.public_inspection_sample())
            self.sync_events();result.update(check_reply=reply, feedback=reply['content'],no_op=reply['no_op'])
            if reply['decision'] == 'accepted' and not self._outer_update_sent and public_ledger(self.history)['inspection_required']:
                self._outer_update_sent = True
                self._append(dict(kind='proposal', proposal_id='outer1', binding='outer_blue',
                                  destination=self.outer_update['destination'],content='提议仅调整有效外层blue目的地；当前检查与red/green工作不变。'))
                self._append(dict(kind='proposal_reply',proposal_id='outer1',decision=self.outer_update['decision'],
                                  content='接受外层提议。' if self.outer_update['decision']=='accept' else '拒绝外层提议。'))
        elif choice == 'request_return':
            self.cost['requests_return'] += 1
            if self.world.return_start_tick is not None:
                result.update(no_op=True,feedback='返程已启动，重复请求不重启。')
            elif self.world.delivery_event is None or not (
                abs(self.world.delivery_facts()['carrier_joint']) < TRANSPORT['carrier_goal_joint_tolerance'] and
                abs(self.world.delivery_facts()['carrier_speed']) < TRANSPORT['carrier_speed_limit']):
                result.update(valid=False,feedback='载台尚未实际交付且稳定在已核验终点，返程未启动。')
            else:
                result['motion'] = self.world.start_return();result['feedback'] = '接受返回请求，开始实际返程；载荷事实由实际承载判断。'
                self._append(dict(kind='return_request_accepted',motion=result['motion'],content=result['feedback']))
        elif choice == 'yield':
            self.cost['yields'] += 1;start = self.world.tick;baseline = len(self.pending_events)
            for _ in range(CONFIG['yield_limit_ticks']):
                self.world.simulate(1)
                if len(self.pending_events) > baseline:break
            self.cost['wait_ticks'] += self.world.tick-start
            result.update(wait_ticks=self.world.tick-start,
                          feedback='等待期间已观察新的实际公共里程碑。' if len(self.pending_events)>baseline else '实际等待窗口结束，未出现新的公共里程碑。')
        elif choice in {entry['id'] for entry in MENU}:
            _, item, target = choice.split('_')
            actual = [region for region in ('left','right','inspection')
                      if (region != 'inspection' or item == 'blue') and self.world.at_goal(item,region)]
            carrier = self.world.delivery_facts()
            blue_source_ok = bool(actual) or carrier['satisfied']
            if item == 'blue' and not blue_source_ok:
                result.update(valid=False,feedback='blue不在已核验的稳定盘/检查来源或当前稳定交付载台，未执行。')
            elif target in actual:
                result.update(no_op=True,feedback=f'{item}实际已在所选区域{target}，未重复抓放。')
            else:
                execution = self.world.pick_place(item,target,'careful' if item in ('red','green') else 'direct')
                self.cost['physical_attempts'] += int(execution['physical_attempt'])
                self.cost['physical_failures'] += int(execution['physical_attempt'] and not execution['success'])
                actual = [region for region in ('left','right','inspection')
                          if (region != 'inspection' or item == 'blue') and self.world.at_goal(item,region)]
                result.update(execution=execution,feedback=f'物理执行结果：{execution["reason"]}；{item}实际区域{actual}。')
                if not execution['success']:self.terminated=True;self.termination_reason='physical_failure'
        else:result.update(valid=False,feedback='未知候选，未执行。')
        self.cost['invalid'] += int(not result['valid']);self.cost['no_ops'] += int(result['no_op'])
        self.sync_events();self._append(dict(kind='action_feedback',choice=choice,content=result['feedback']))
        if not self.terminated and self.cost['decisions'] >= CONFIG['decision_budget']:
            self.terminated=True;self.termination_reason='budget_exhausted'
        result.update(terminated=self.terminated,termination_reason=self.termination_reason)
        return copy.deepcopy(result)


def reference(observation, policy):
    ledger = public_ledger(observation['history']);regions = observation['physical_placements']
    if not ledger['transport_started']:return 'request_transport'
    if 'left' not in regions['red']:return 'careful_red_left'
    if ledger['inspection_required'] and not ledger['check_completed']:
        if observation['delivery_event'] is None:return 'yield'
        if 'inspection' not in regions['blue']:return 'place_blue_inspection'
        near = observation['physical']['presence']['near'] and observation['physical']['presence_motion'] is None
        if not ledger['child_active']:
            return 'request_check' if near else 'yield'
        if policy == 'public_ledger_progress' and 'right' not in regions['green']:return 'careful_green_right'
        return 'yield'
    if 'right' not in regions['green']:return 'careful_green_right'
    if observation['delivery_event'] is None:return 'yield'
    if ledger['blue_role'] == 'partner_return':
        if observation['carrier_return_event'] is None:
            requested = any(e['kind']=='return_request_accepted' for e in observation['history'])
            return 'yield' if requested else 'request_return'
        if observation['payload_return_event'] is None:return 'yield'
    elif ledger['goals']['blue'] not in regions['blue']:
        return 'place_blue_' + ledger['goals']['blue']
    if ledger['carrier_return_required'] and observation['carrier_return_event'] is None:
        requested = any(e['kind']=='return_request_accepted' for e in observation['history'])
        return 'yield' if requested else 'request_return'
    return 'declare_done'
