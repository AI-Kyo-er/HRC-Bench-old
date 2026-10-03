"""仅公开已发生事务归约目标，green表达依赖当前有效blue；无目标执行gate。"""
import copy
import json
from pathlib import Path
from experiments.sustained_structure_v21.service import InspectionService
from experiments.sustained_combination_v23.protocol import MENU as ORIGINAL_MENU,WORKSPACE
from experiments.structure_foundation_v20.audit_v2 import stable_region

CONFIG=json.loads(Path(__file__).with_name('config.json').read_text())
MENU=copy.deepcopy(ORIGINAL_MENU)
SYSTEM='''这是一个同一World/物理时钟中的持续共同活动，已经完成的工作和公开历史保留。机器人负责blue，red-left、真实检查贡献、载台当前远端稳定和blue/green当前有效要求都需满足。
初始公开blue目标和green要求见已接受历史。本活动有一次blue目标确认，确认pending时尚未结束；拒绝也关闭确认但不改变blue目标，只有绑定该提议的接受才更新有效blue约定。green直接目标固定不联动；same/opposite关系始终按最新已生效blue约定求值。未回应提议不能生效，也不要把检查交还当成取消或回滚外层约定。
确认在公开约定的检查前或实际检查交还时发送。检查后消息在handoff同一真实tick生成，技能不可打断，下一动作边界观察。动作开始后才发生的更新不当作此前已经可知；此前符合约定的green放置因新约定失效需重新整理，不追溯称违规。最终目标不是全程位置禁令，暂存和移动允许，检查合格采样前提不满足时暂停。
request_check仅blue实际稳定支撑检查台、presence实际近端稳定无运动且机器人不再接触blue时接受；合格支持/速度/在场条件累计240真实tick才公开交还，不需要finish。presence本轮stay。请求过早拒绝不排队，重复不清零。职责及目标更新不免检查、不清已有进度。
12能力菜单所有条件相同。request_transport只在当前载台far稳定且无active时接受前送，request_return只在near稳定且无active时接受返程；可空载，重复同向不重启、运动反向拒绝不排队。blue抓放只按核验稳定来源和无活动载台，reload还需当前near，不能按正确目标/检查完成筛动作。workspace公开轨道/支撑/槽位和right扫掠，允许简单等待/red-first/暂存。
yield只推进实际物理至新公共里程碑或1920tick，不自动请求；旧事件不造成零tick循环。反馈仅实际区域/支撑/公开响应，不给正确下一步。declare_done随时真终止、不纠错；只同步已发生事件，不生成未来确认。终止后独立验收pending关闭、检查完成、red-left、当前far和blue/green要求。预算见remaining_decisions，所有拒绝/非法/声明耗一步，技能停车/等待实际计时，交流无模拟时长。局部测量前缀由实验参考真实执行，后续12步另列，前缀不是局部策略自主工作。只输出唯一字符串字段choice的JSON对象。
'''


def opposite(target):return 'right' if target=='left' else 'left'


def candidates():return copy.deepcopy(MENU)


def public_ledger(history):
    goals={};green=None;pending={};seen=set();confirmation_pending=True;active=completed=False;progress=0
    for event in history:
        kind=event['kind']
        if kind=='accepted_activity':goals=dict(event['goals']);green=copy.deepcopy(event['green_requirement'])
        elif kind=='confirmation_announced':confirmation_pending=True
        elif kind=='proposal':
            ident=event['proposal_id']
            if ident in seen:raise ValueError('提议ID重复。')
            seen.add(ident);pending[ident]=copy.deepcopy(event)
        elif kind=='proposal_reply':
            ident=event['proposal_id']
            if ident not in pending or event['decision'] not in ('accept','reject'):raise ValueError('回应必须绑定尚未回复的提议。')
            proposal=pending.pop(ident)
            if proposal['binding']!='outer_blue':raise ValueError('未知目标绑定。')
            if event['decision']=='accept':goals['blue']=proposal['destination']
            confirmation_pending=False
        elif kind=='check_request_reply':
            progress=event['qualified_ticks']
            if event['decision']=='accepted':active=True
        elif kind=='partner_check_handoff':active=False;completed=True;progress=event['qualified_ticks']
    if green is not None:goals['green']=green['destination'] if green['mode']=='direct' else goals['blue'] if green['relation']=='same' else opposite(goals['blue'])
    return dict(goals=goals,green_requirement=green,confirmation_pending=confirmation_pending,pending_proposals=pending,child_active=active,check_completed=completed,check_progress_observed=progress)


class Episode:
    def __init__(self,world,initial_blue,green_requirement,reply,timing):
        self.world=world;self.history=[];self.pending_events=[];self._cycle_cursor=0;self._confirmation_sent=False
        self.timing=timing;self._update=dict(destination=opposite(initial_blue),decision='accept' if reply=='accepted' else 'reject')
        self.terminated=False;self.termination_reason=None;self.budget_origin=0;self.decision_budget=CONFIG['decision_budget']
        self.cost=dict(decisions=0,invalid=0,requests_transport=0,requests_return=0,requests_check=0,yields=0,wait_ticks=0,physical_attempts=0,physical_failures=0,no_ops=0,declarations=0,reloads=0)
        self._append(dict(kind='background_source',content='脚本共同接受/确认提议回应、运动代理及240tick模拟检查贡献，非真人；策略动作另记。'))
        self._append(dict(kind='accepted_activity',goals=dict(red='left',blue=initial_blue),green_requirement=copy.deepcopy(green_requirement),inspection_required=True,carrier_return_required=True,blue_role='robot',content='共同接受物品要求、模拟检查和当前载台最终far稳定；已有进展保留。'))
        self._append(dict(kind='accepted_presence_clause',clause='stay',content='当前presence留近端提供模拟检查。'))
        self._append(dict(kind='confirmation_announced',confirmation_id=CONFIG['confirmation_id'],timing=timing,content='本活动还有一次blue目标确认；完成检查、等待确认关闭并满足物品要求后再声明。'))
        self.service=InspectionService('stay',self._emit,world.start_presence);world.step_callback=self._on_tick
        if timing=='before_check':self._generate_update(world.tick);self.sync_events()

    def _append(self,event):
        event=copy.deepcopy(event);event.setdefault('actual_tick',self.world.tick);event.update(event_sequence=len(self.history),observed_tick=self.world.tick);self.history.append(event)

    def _generate_update(self,tick):
        if self._confirmation_sent:return
        self._confirmation_sent=True;ident=CONFIG['confirmation_id']
        self.pending_events.extend([dict(kind='proposal',proposal_id=ident,binding='outer_blue',destination=self._update['destination'],actual_tick=tick,content='提议将blue有效外层投递目标调整为'+self._update['destination']+'；检查义务和其他已接受要求保留。'),
            dict(kind='proposal_reply',proposal_id=ident,decision=self._update['decision'],actual_tick=tick,content='接受该blue目标提议。' if self._update['decision']=='accept' else '拒绝该blue目标提议，保留现有效约定。')])

    def _emit(self,event):
        self.pending_events.append(copy.deepcopy(event))
        if event['kind']=='partner_check_handoff' and self.timing=='after_handoff':self._generate_update(event['actual_tick'])

    def _on_tick(self,facts):
        result=self.service.step(facts)
        for event in self.world.cycle.events[self._cycle_cursor:]:
            self._emit(dict(kind='physical_cycle_event',actual_tick=event['first_tick'],event=copy.deepcopy(event),content='当前行程实际物理里程碑，旧事件不替代当前事实。'))
        self._cycle_cursor=len(self.world.cycle.events);result['events_so_far']=copy.deepcopy(self.pending_events);return result

    def sync_events(self):
        for event in self.pending_events:self._append(event)
        self.pending_events.clear()

    def observation(self):
        self.sync_events();s=self.world.state();cycle=s['cycle']
        return copy.deepcopy(dict(history=self.history,physical=dict(objects=s['objects'],carrier=s['current_carrier_facts'],presence=s['presence'],presence_motion=s['presence_motion'],inspection=s['inspection_facts']),
            physical_placements={i:[r for r in ('left','right','inspection','carrier') if (r not in ('inspection','carrier') or i=='blue') and self.world.at_goal(i,r)] for i in ('red','blue','green')},
            motion={k:cycle[k] for k in ('active','legs','events')},workspace=WORKSPACE,candidates=candidates(),remaining_decisions=self.decision_budget-(self.cost['decisions']-self.budget_origin)))

    def messages(self):return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(self.observation(),ensure_ascii=False))]

    def begin_local(self):
        self.sync_events();ledger=public_ledger(self.history)
        assert ledger['check_completed'] and not ledger['confirmation_pending'] and self.world.cycle.active is None and self.world.carrier_facts()['far']
        self.budget_origin=self.cost['decisions'];self.decision_budget=CONFIG['local_decision_budget']
        self._append(dict(kind='local_measurement_start',current_blue_destination=ledger['goals']['blue'],green_requirement=ledger['green_requirement'],prefix_decisions=self.budget_origin,local_decision_budget=12,content='实验参考已真实执行前缀；当前已生效blue约定和green要求如列，局部12决策从此计，前缀不是局部策略自主完成。'))

    def act(self,choice):
        if self.terminated:raise RuntimeError('活动终止，物理/历史/成本不再推进。')
        self.sync_events();self.cost['decisions']+=1;result=dict(choice=choice,valid=True,no_op=False)
        if choice=='declare_done':
            self.cost['declarations']+=1;self.terminated=True;self.termination_reason='declared_done';result['feedback']='收到完成声明，活动实际结束。'
        elif choice in ('request_transport','request_return'):
            self.cost['requests_transport' if choice=='request_transport' else 'requests_return']+=1
            reply=self.world.request_motion('forward' if choice=='request_transport' else 'return');result.update(motion_reply=reply,valid=reply['decision'] in ('accepted','already_running'),no_op=reply['decision']=='already_running',feedback='当前物理请求响应'+reply['decision']+'，拒绝不排队、重复不重启。')
            self._append(dict(kind='cycle_request_reply',reply=reply,content=result['feedback']))
        elif choice=='request_check':
            self.cost['requests_check']+=1;reply=self.service.request(self.world.public_inspection_sample());self.sync_events();result.update(check_reply=reply,valid=reply['decision']!='rejected',no_op=reply['no_op'],feedback=reply['content'])
        elif choice=='yield':
            self.cost['yields']+=1;start=self.world.tick;baseline=len(self.pending_events)
            for _ in range(CONFIG['yield_limit_ticks']):
                self.world.simulate(1)
                if len(self.pending_events)>baseline:break
            result.update(wait_ticks=self.world.tick-start,feedback='真实等待到新公共事件或窗口上限。');self.cost['wait_ticks']+=result['wait_ticks']
        elif choice in {c['id'] for c in MENU}:
            if choice=='reload_blue':item,target='blue','carrier';self.cost['reloads']+=1
            else:_,item,target=choice.split('_')
            if self.world.at_goal(item,target):result.update(no_op=True,feedback=f'{item}实际已在所选区域{target}，未重复抓放。')
            else:
                execution=self.world.pick_place(item,target,'careful' if item in ('red','green') else 'direct');attempted=execution['physical_attempt']
                self.cost['physical_attempts']+=int(attempted);self.cost['physical_failures']+=int(attempted and not execution['success'])
                actual=[r for r in ('left','right','inspection','carrier') if (r not in ('inspection','carrier') or item=='blue') and self.world.at_goal(item,r)]
                result.update(execution=execution,valid=execution['success'],feedback=f'物理响应{execution["reason"]}；{item}实际区域{actual}。')
                if attempted and not execution['success']:self.terminated=True;self.termination_reason='physical_failure'
        else:result.update(valid=False,feedback='未知候选，未执行。')
        self.cost['invalid']+=int(not result['valid']);self.cost['no_ops']+=int(result['no_op']);self.sync_events();self._append(dict(kind='action_feedback',choice=choice,content=result['feedback']))
        if not self.terminated and self.cost['decisions']-self.budget_origin>=self.decision_budget:self.terminated=True;self.termination_reason='budget_exhausted'
        result.update(terminated=self.terminated,termination_reason=self.termination_reason);return copy.deepcopy(result)


def reference(obs):
    ledger=public_ledger(obs['history']);regions=obs['physical_placements'];motion=obs['motion'];cf=obs['physical']['carrier']
    if not motion['legs']:return 'request_transport'
    if 'left' not in regions['red']:return 'careful_red_left'
    if motion['active'] is not None:return 'yield'
    if not ledger['check_completed']:
        if not cf['near']:return 'request_transport' if cf['far'] else 'yield'
        if 'inspection' not in regions['blue']:return 'place_blue_inspection'
        return 'yield' if ledger['child_active'] else 'request_check'
    if ledger['confirmation_pending']:return 'yield'
    if not cf['far']:return 'request_return' if cf['near'] else 'yield'
    for item,prefix in (('blue','place'),('green','careful')):
        if ledger['goals'][item] not in regions[item]:return prefix+'_'+item+'_'+ledger['goals'][item]
    return 'declare_done'


def terminal_score(ep,state):
    ledger=public_ledger(ep.history);cf=state['current_carrier_facts']
    facts=dict(confirmation_closed=not ledger['confirmation_pending'] and not ledger['pending_proposals'],check_completed=ep.service.completed,no_active_child=not ledger['child_active'],
        red_left=stable_region(state,'red','left'),blue_current_goal=stable_region(state,'blue',ledger['goals']['blue']),green_current_goal=stable_region(state,'green',ledger['goals']['green']),carrier_current_far=cf['far'] and state['cycle']['active'] is None)
    return dict(facts=facts,task_success=all(facts.values()) and ep.termination_reason=='declared_done')
