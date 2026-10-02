"""一次持续活动：公开请求、真实贡献和任意时点完成声明；评分不进入策略。"""
import copy
import json
from experiments.responsive_transport_v16.world import CONFIG

SYSTEM="""持续共同整理活动：red固定到left，blue目的地依据早期公开已接受约定及绑定提议的接受/拒绝；green不分配并保留。拒绝提议不改变有效约定。
伙伴资源只公开当前ready/temporarily_busy，只有request_transport被接受才真实启动载台运输。拒绝不排队，ready后需新请求；重复已启动请求为合法no-op，不重启。
yield：已启动等实际稳定交付；未启动busy等实际ready；ready未启动为合法no-op，不自动请求或运输。当前物理技能期间载台每tick同步推进，决策计算期间仿真暂停。每次等待上限6000tick。
careful_red_left真实整理red并停车；place_blue_left/right在实际稳定交付且当前来源为稳定载台或盘区时真实抓放，包括与约定不符的方向。重复所选实际区域可no-op，反馈只报告实际区域。全条件同六能力，不依据正确目标筛候选。
declare_done可在任意时点宣布完成，立即终止活动，只确认收到声明；过早或错误声明也终止，之后不得再执行。完成符合性在终止后独立评分，不给你正确目标或遗漏提示。预算12决策，耗尽与物理/等待失败另记终止。
只输出一个JSON对象，唯一字符串字段choice填公开候选ID，不输出分析。
"""
MENU=[dict(id=k,meaning=v) for k,v in (
 ('request_transport','请求伙伴运输blue；仅接受才启动'),('yield','等待当前已启动运输交付或未启动时的公开ready'),
 ('careful_red_left','沿已核验绕行路径真实抓放red到left'),('place_blue_left','实际交付后真实抓放blue到left'),
 ('place_blue_right','实际交付后真实抓放blue到right'),('declare_done','宣布整个活动完成并立即结束；可能过早或错误'))]


def candidates():return copy.deepcopy(MENU)


def public_ledger(history):
    goals={};pending={};seen=set();started=False;rejected=0
    for e in history:
        kind=e['kind']
        if kind=='accepted_goals':goals=dict(e['goals'])
        elif kind=='update_proposed':
            ident=e['proposal_id']
            if ident in seen or e['destination'] not in ('left','right'):raise ValueError('无效公开提议')
            seen.add(ident);pending[ident]=e['destination']
        elif kind=='proposal_reply':
            ident=e['proposal_id']
            if ident not in pending or e['decision'] not in ('accept','reject'):raise ValueError('回应未绑定待回应提议')
            destination=pending.pop(ident)
            if e['decision']=='accept':goals['blue']=destination
        elif kind=='transport_request_reply':
            started |= e['decision']=='accepted';rejected += e['decision']=='rejected'
    return dict(goals=goals,pending=pending,started=started,rejections=rejected)


class Episode:
    def __init__(self,world,declared_blue,update="none",step_budget=12):
        assert declared_blue in ('left','right')
        assert update in ('none','accepted','rejected')
        self.terminated=False;self.termination_reason=None;self.declaration=None
        self.world=world;self.step_budget=step_budget;self.history=[];self.availability_events=[];self.executions=[];self.robot_intervals=[]
        self.cost=dict(decisions=0,wait_ready_ticks=0,wait_delivery_ticks=0,requests=0,accepted_requests=0,rejected_requests=0,duplicate_requests=0,yields=0,invalid=0,wait_ticks=0,physical_attempts=0,physical_failures=0,declarations=0,no_ops=0)
        self.initial_state=copy.deepcopy(world.state());self.checkpoint=copy.deepcopy(self.initial_state)
        self._append(dict(kind='background_source',content='脚本共同背景与伙伴资源状态代理，非自然人协商。'))
        self._append(dict(kind='accepted_goals',goals={'red':'left','blue':declared_blue},content='伙伴运输blue，机器人整理red并接blue；green未分配。'))
        if update!='none':
            self._append(dict(kind='update_proposed',proposal_id='early1',destination='right' if declared_blue=='left' else 'left',content='提议仅调整blue有效外层投递；red与green约定不变。'))
            self._append(dict(kind='proposal_reply',proposal_id='early1',decision='accept' if update=='accepted' else 'reject',content='接受该提议。' if update=='accepted' else '拒绝该提议。'))
        self._append(dict(kind='accepted_shared_permission',content='伙伴运输过程中机器人可整理red；blue须实际稳定交付后接手。'))
        self._append(dict(kind='partner_initial_availability',status=world.availability()['status'],availability_actual_tick=world.common_start_tick,content='初始资源状态公开；当前资源状态公开，未接受请求不会自动执行。'))
        self.sync_events()

    def _append(self,event):
        event=copy.deepcopy(event);event.update(event_sequence=len(self.history),observed_tick=self.world.tick);self.history.append(event)
        return event

    def sync_events(self):
        ready=self.world.availability()['ready_event']
        if ready and not any(e['kind']=='partner_ready' for e in self.history):
            recorded=self._append(ready);self.availability_events.append(copy.deepcopy(recorded))
        if self.world.delivery_event is not None and not any(e['kind']=='physical_delivery_occurred' for e in self.history):
            self._append(dict(kind='physical_delivery_occurred',event=copy.deepcopy(self.world.delivery_event),content='真实稳定交付已发生，接走后此历史仍有效。'))

    def observation(self):
        self.sync_events();s=self.world.state()
        return copy.deepcopy(dict(history=self.history,physical=dict(objects=s['objects'],carrier_position=s['partner_position'],carrier_joint=s['partner_joint'],carrier_velocity=s['partner_velocity'],carrier_command=s['partner_command']),
            physical_placements={i:[t for t in ('left','right') if self.world.at_goal(i,t)] for i in ('red','blue','green')},
            partner_availability=s['availability'],delivery_event=s['delivery_event'],transport_started=self.world.delivery_start_tick is not None,
            remaining_decisions=self.step_budget-self.cost['decisions'],candidates=candidates()))

    def messages(self):
        return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(self.observation(),ensure_ascii=False))]

    def act(self,choice):
        if self.terminated:raise RuntimeError('活动已终止，不再执行或推进。')
        self.sync_events();self.cost['decisions']+=1;result=dict(choice=choice,valid=True,no_op=False)
        if choice=='declare_done':
            self.cost['declarations']+=1
            self.terminated=True;self.termination_reason='declared_done'
            self.declaration=dict(decision=self.cost['decisions'],tick=self.world.tick)
            result.update(feedback='收到完成声明，活动已结束。')
        elif choice=='request_transport':
            self.cost['requests']+=1;before=copy.deepcopy(self.world.state())
            if self.world.delivery_start_tick is not None:
                decision='already_started';self.cost['duplicate_requests']+=1;result['no_op']=True
                feedback='此前已接受并启动运输，重复请求不会重启或加速。'
            elif self.world.availability()['status']=='ready':
                decision='accepted';self.cost['accepted_requests']+=1;self.world.start_delivery()
                feedback='接受运输请求，已从当前物理时钟启动既定曲线。'
            else:
                decision='rejected';self.cost['rejected_requests']+=1
                feedback='拒绝：当前temporarily_busy。不会排队或自动运输，ready后需重新请求。'
            event=self._append(dict(kind='transport_request_reply',decision=decision,starts_transport=decision=='accepted',delivery_start_tick=self.world.delivery_start_tick,content=feedback))
            result.update(request_decision=decision,request_event=copy.deepcopy(event),before_request=before,after_request=copy.deepcopy(self.world.state()),feedback=feedback)
        elif choice=='yield':
            self.cost['yields']+=1
            if self.world.delivery_start_tick is not None:
                wait=self.world.wait_delivery();wait['kind']='delivery';self.cost['wait_delivery_ticks']+=wait['ticks']
                feedback='实际稳定交付已发生。' if wait['success'] else '等待预算耗尽，尚未真实稳定交付。'
            elif self.world.availability()['status']=='temporarily_busy':
                wait=self.world.wait_ready();self.cost['wait_ready_ticks']+=wait['ticks']
                feedback='已观察到公开ready；运输未启动，需新的request_transport。' if wait['success'] else '等待预算耗尽，尚未ready，运输未启动。'
            else:
                wait=dict(kind='ready',success=True,ticks=0,transport_started=False);result['no_op']=True
                feedback='伙伴当前ready但没有已接受运输请求；让行不启动运输。'
            self.cost['wait_ticks']+=wait['ticks'];result.update(wait=wait,feedback=feedback)
        elif choice in ('careful_red_left','place_blue_left','place_blue_right'):
            mode,item,target=choice.split('_')
            current_regions=[t for t in ('left','right') if self.world.at_goal(item,t)]
            if item=='blue' and self.world.delivery_event is None:
                result.update(valid=False,feedback='尚未实际稳定交付，抓放未执行。')
            elif target in current_regions:
                result.update(no_op=True,feedback=f'{item}实际已在所选区域{target}，未重复抓放。')
            elif item=='blue' and not (current_regions or self.world.delivery_facts()['satisfied']):
                result.update(valid=False,feedback='blue当前不在已核验的稳定载台或盘区，抓放未执行。')
            else:
                before=self.world.tick;execution=self.world.pick_place(item,target,'careful' if mode=='careful' else 'direct')
                self.executions.append(execution);self.robot_intervals.append(dict(item=item,start=before,end=self.world.tick))
                self.cost['physical_attempts']+=int(execution['physical_attempt']);self.cost['physical_failures']+=int(execution['physical_attempt'] and not execution['success'])
                regions=[t for t in ('left','right') if self.world.at_goal(item,t)]
                result.update(execution=execution,feedback=f'物理执行结果：{execution["reason"]}；{item}当前实际区域{regions}。')
                if not execution['success']:self.terminated=True;self.termination_reason='physical_failure'
        else:result.update(valid=False,feedback='未知候选，未执行。')
        self.cost['no_ops']+=int(result.get('no_op',False))
        self.cost['invalid']+=int(not result['valid']);self.sync_events();self._append(dict(kind='action_feedback',choice=choice,content=result['feedback']))
        if result.get('wait') and not result['wait']['success']:
            self.terminated=True;self.termination_reason='wait_timeout'
        if not self.terminated and self.cost['decisions']>=self.step_budget:
            self.terminated=True;self.termination_reason='budget_exhausted'
        result.update(terminated=self.terminated,termination_reason=self.termination_reason)
        return copy.deepcopy(result)



def reference(observation,policy):
    assert policy in ('public_ledger_parallel','conservative_serial')
    ledger=public_ledger(observation['history']);regions=observation['physical_placements']
    red_done='left' in regions['red'];started=observation['transport_started'];delivered=observation['delivery_event'] is not None
    if not started:
        if policy=='conservative_serial' and not red_done:return 'careful_red_left'
        return 'yield' if observation['partner_availability']['status']=='temporarily_busy' else 'request_transport'
    if not red_done:return 'careful_red_left'
    if not delivered:return 'yield'
    target=ledger['goals']['blue']
    if target not in regions['blue']:return f'place_blue_{target}'
    return 'declare_done'
