"""伙伴请求/接受真正启动运输，规则只接收公开观察。"""
import copy
import json
from experiments.physical.protocol import candidates as base_candidates
from experiments.responsive_transport_v16.world import CONFIG

SYSTEM='''持续共同任务：red与blue到left，green未分配应保留；伙伴载台摩擦运输blue，你整理red并在稳定交付后接blue。
伙伴初始公开ready或temporarily_busy；可用性随真实物理时钟变化，只读取公开当前状态。只有request_transport被接受才启动既定真实运输；拒绝不排队，不会因随后ready而自动启动，需重新请求。
已启动后的重复运输请求为合法no-op，不重启/加速曲线。每个请求接受、拒绝或重复都计1决策，反馈不模拟说话时间，0物理tick。
共享许可：运输中可先整理red。blue只有真实稳定交付后才可接手；yield在已启动时等稳定交付，未启动且busy时等公开ready；ready未启动时合法no-op，不启动或加速运输。request_clear只请求清道，不启动运输、不授予assisted。
候选为全部21通用能力，包含错误目标和暂不可执行动作，拒绝反馈允许重试。place直接抓放，careful绕行，assisted需已接受清道协助。
稳定交付由实际载台/blue相对位姿、速度、承载接触共同首次满足，历史事件在接走blue后保留。
只输出一个JSON对象，唯一字符串字段choice填公开候选ID，不输出解释。
'''


def candidates():
    return base_candidates()+[dict(id='request_transport',meaning='请求伙伴执行既定blue载台运输；只有接受才启动，拒绝后需重新请求')]


def cases():
    return [dict(id=f'Transport_{availability}_{policy}_{seed}',seed=seed,initial_availability=availability,policy=policy,step_budget=8)
        for seed in (80,81) for availability in ('ready','temporarily_busy') for policy in ('availability_greedy','serial','eager','wait_ready')]


def public_ledger(history):
    goals={};requested=False;started=False;rejected=0
    for e in history:
        if e['kind']=='accepted_goals':goals=dict(e['goals'])
        if e['kind']=='transport_request_reply':
            requested=True
            if e['decision']=='accepted':started=True
            if e['decision']=='rejected':rejected+=1
    return dict(goals=goals,requested=requested,started=started,rejections=rejected)


class Episode:
    def __init__(self,world,step_budget=8):
        self.world=world;self.step_budget=step_budget;self.history=[];self.availability_events=[];self.executions=[];self.robot_intervals=[]
        self.cost=dict(decisions=0,wait_ready_ticks=0,wait_delivery_ticks=0,requests=0,accepted_requests=0,rejected_requests=0,duplicate_requests=0,clear_requests=0,yields=0,invalid=0,wait_ticks=0,physical_attempts=0,physical_failures=0)
        self.initial_state=copy.deepcopy(world.state());self.checkpoint=copy.deepcopy(self.initial_state)
        self._append(dict(kind='background_source',content='脚本共同背景与伙伴资源状态代理，非自然人协商。'))
        self._append(dict(kind='accepted_goals',goals={'red':'left','blue':'left'},content='伙伴运输blue，机器人整理red并接blue；green未分配。'))
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

    def success(self):
        return self.world.delivery_event is not None and all(self.world.at_goal(i,t) for i,t in public_ledger(self.history)['goals'].items())

    def act(self,choice):
        self.sync_events();self.cost['decisions']+=1;result=dict(choice=choice,valid=True,no_op=False)
        if choice=='request_transport':
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
        elif choice=='request_clear':
            self.cost['clear_requests']+=1;result.update(no_op=True,feedback='清道请求不启动运输，不授予assisted；可单独request_transport。')
        elif choice in {c['id'] for c in candidates()}:
            mode,item,target=choice.split('_');goals=public_ledger(self.history)['goals']
            if item not in goals:result.update(valid=False,feedback='green未分配，应保留。')
            elif target!=goals[item]:result.update(valid=False,feedback=f'公开目标为{item}到{goals[item]}。')
            elif item=='blue' and self.world.delivery_event is None:result.update(valid=False,feedback='blue尚未真实稳定交付，抓放未执行。')
            elif self.world.at_goal(item,target):result.update(valid=False,feedback='已在约定区域，抓放未执行。')
            elif mode=='assisted':result.update(valid=False,feedback='无已接受清道协助，抓放未执行。')
            else:
                before=self.world.tick;execution=self.world.pick_place(item,target,'careful' if mode=='careful' else 'direct')
                self.executions.append(execution);self.robot_intervals.append(dict(item=item,start=before,end=self.world.tick))
                self.cost['physical_attempts']+=int(execution['physical_attempt']);self.cost['physical_failures']+=int(execution['physical_attempt'] and not execution['success'])
                result.update(execution=execution,feedback=execution['reason'])
        else:result.update(valid=False,feedback='未知候选，未执行。')
        self.cost['invalid']+=int(not result['valid']);self.sync_events();self._append(dict(kind='action_feedback',choice=choice,content=result['feedback']))
        result['success']=self.success();return copy.deepcopy(result)


def reference(observation,policy):
    """三种独立算法；只接收公开obs和固定算法名，无world/case/未来plan。"""
    assert policy in ('availability_greedy','serial','eager','wait_ready')
    ledger=public_ledger(observation['history']);started=observation['transport_started'];delivered=observation['delivery_event'] is not None
    red_done=ledger['goals']['red'] in observation['physical_placements']['red']
    if not started:
        if red_done:return 'request_transport'
        if policy=='wait_ready':return 'yield' if observation['partner_availability']['status']=='temporarily_busy' else 'request_transport'
        if policy=='serial':return 'careful_red_left'
        if policy=='availability_greedy' and observation['partner_availability']['status']!='ready':return 'careful_red_left'
        if policy=='eager' and ledger['requested']:return 'careful_red_left'
        return 'request_transport'
    if not red_done:return 'careful_red_left'
    if not delivered:return 'yield'
    if ledger['goals']['blue'] not in observation['physical_placements']['blue']:return 'place_blue_left'
    raise ValueError('公开任务已完成。')
