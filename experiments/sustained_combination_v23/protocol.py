"""检查与最新blue职责合取；执行门槛仅真实来源/端点。"""
import copy
import json
from pathlib import Path
from experiments.sustained_structure_v21.protocol import Episode as ParentEpisode,public_ledger,MENU as PARENT_MENU
from experiments.sustained_structure_v21.service import InspectionService
from experiments.transport_cycle_v22.run import WORKSPACE
from experiments.structure_foundation_v20.audit_v2 import stable_region

CONFIG=json.loads(Path(__file__).with_name('config.json').read_text())
MENU=copy.deepcopy(PARENT_MENU)+[dict(id='reload_blue',meaning='从核验稳定盘/检查台真实重装当前近端稳定载台')]
for entry in MENU:
    if entry['id']=='request_transport':entry['meaning']='请求一次实际前送；仅远端稳定无运动接受，可空载或载blue'
    if entry['id']=='request_return':entry['meaning']='请求一次实际返程；仅近端稳定无运动接受，可空载或载blue'
SYSTEM='''这是一个持续共同活动，全部动作/载台/presence/模拟检查共享同一World和时钟，已有进度和全部行程历史保留。
公开初始red-left、green-right、blue机器人L/R目标、检查贡献和载台最终远端稳定都需履行。提议绑定回应，仅接受改变blue职责，拒绝保留机器人L/R；职责变化不免检查、不清目标/进度。检查交还后依最新有效职责继续。
request_transport只在当前载台远端稳定且无活动运动时接受前送，request_return只在当前近端稳定且无活动运动时接受返程。重复同向不重启，运动中反向拒绝不排队。每次实际接受产生新行程；空载到位不代表载blue到位，旧delivery/return历史不代表当前来源或完成。
blue稳定检查台且伙伴实际近端稳定、无运动、机器人不再接触blue时request_check接受；早到/不在场拒绝不排队。检查按真实支持、位置/速度和在场条件累计240合格tick；移动blue可暂停，不语义拦截。retain实际退出保承诺/进度，返近继续；withdraw公开撤销承诺保进度，返近需新请求；完成后伙伴真实贡献交还，不使用机器人finish。
12能力菜单所有条件一致。reload/blue抓放须载台无活动运动且blue来自核验稳定盘/检查台或当前近端承载；reload另需近端稳定。动作不按正确目标、当前职责或检查完成筛选；错误目标和提前返程可真实执行并在公共事实允许时恢复。工作空间含扫掠范围，green-right位于返程方向，允许简单等待/暂存调度。
yield等下一条新公共里程碑或1920tick上限，旧事件不重复零tick触发；等待不自动请求。技能期间伙伴每tick推进，高层动作边界观察消息。反馈只报实际区域/支持/公开请求响应，不给正确下一步。
declare_done任何时点实际终止，不纠错；目标/职责/贡献终止后私有验收，不进入策略。预算48决策，非法/拒绝同样耗一步，无模拟说话时长。只输出唯一字符串字段choice的JSON对象。
'''


def candidates():return copy.deepcopy(MENU)


class Episode(ParentEpisode):
    def __init__(self,world,declared_blue,reply,presence_clause):
        self.world=world;self.history=[];self.pending_events=[]
        self.terminated=False;self.termination_reason=None
        self._role_sent=False;self._cycle_event_cursor=0;self.role_reply='accept' if reply=='accepted' else 'reject'
        self.cost=dict(decisions=0,invalid=0,requests_transport=0,requests_check=0,requests_return=0,yields=0,
            wait_ticks=0,physical_attempts=0,physical_failures=0,no_ops=0,declarations=0,reloads=0)
        self._append(dict(kind='background_source',content='脚本共同背景和回应、运动代理与模拟观测服务，非自然人。'))
        self._append(dict(kind='accepted_activity',goals=dict(red='left',green='right',blue=declared_blue),blue_role='robot',
            inspection_required=True,carrier_return_required=True,content='共同接受整理/检查贡献和载台最终远端职责，blue初始由机器人按L/R整理。'))
        self._append(dict(kind='accepted_presence_clause',clause=presence_clause,content={'stay':'当前检查可用。','retain':'实际退出保承诺暂停，返近继续。','withdraw':'实际退出公开撤销承诺保进度，返近需新请求。'}[presence_clause]))
        self.service=InspectionService(presence_clause,self._emit,world.start_presence);world.step_callback=self._on_tick

    def _on_tick(self,facts):
        result=self.service.step(facts)
        for event in self.world.cycle.events[self._cycle_event_cursor:]:
            self._emit(dict(kind='physical_cycle_event',actual_tick=event['first_tick'],event=copy.deepcopy(event),content='本行程实际载台/载荷里程碑已发生，旧历史不替代当前状态。'))
        self._cycle_event_cursor=len(self.world.cycle.events)
        result['events_so_far']=copy.deepcopy(self.pending_events);return result

    def observation(self):
        self.sync_events();state=self.world.state();cycle=state['cycle']
        return copy.deepcopy(dict(history=self.history,physical=dict(objects=state['objects'],carrier_position=state['partner_position'],
            carrier=state['current_carrier_facts'],presence=state['presence'],presence_motion=state['presence_motion'],inspection=state['inspection_facts']),
            physical_placements={item:[r for r in ('left','right','inspection','carrier') if (r not in ('inspection','carrier') or item=='blue') and self.world.at_goal(item,r)] for item in ('red','blue','green')},
            motion=dict(active=cycle['active'],legs=cycle['legs'],events=cycle['events']),workspace=WORKSPACE,
            remaining_decisions=CONFIG['decision_budget']-self.cost['decisions'],candidates=candidates()))

    def messages(self):return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(self.observation(),ensure_ascii=False))]

    def act(self,choice):
        if self.terminated:raise RuntimeError('活动已终止，物理/历史/贡献不再推进。')
        self.sync_events();self.cost['decisions']+=1;result=dict(choice=choice,valid=True,no_op=False)
        if choice=='declare_done':
            self.cost['declarations']+=1;self.terminated=True;self.termination_reason='declared_done';result['feedback']='收到完成声明，活动实际结束。'
        elif choice in ('request_transport','request_return'):
            key='requests_transport' if choice=='request_transport' else 'requests_return';self.cost[key]+=1
            reply=self.world.request_motion('forward' if choice=='request_transport' else 'return');result['motion_reply']=reply
            result['valid']=reply['decision'] in ('accepted','already_running');result['no_op']=reply['decision']=='already_running'
            result['feedback']=f'当前物理请求响应：{reply["decision"]}；行程{reply["leg_id"]}，拒绝不排队，重复不重启。'
            self._append(dict(kind='cycle_request_reply',reply=reply,content=result['feedback']))
        elif choice=='request_check':
            self.cost['requests_check']+=1;reply=self.service.request(self.world.public_inspection_sample());self.sync_events()
            result.update(check_reply=reply,valid=reply['decision']!='rejected',no_op=reply['no_op'],feedback=reply['content'])
            if reply['decision']=='accepted' and not self._role_sent:
                self._role_sent=True
                self._append(dict(kind='proposal',proposal_id='role1',binding='blue_role',blue_role='partner_return',content='提议blue最终由伙伴随载接回；检查贡献和red/green、原机器人L/R目标均保留。'))
                self._append(dict(kind='proposal_reply',proposal_id='role1',decision=self.role_reply,content='接受blue分工提议，检查不免除。' if self.role_reply=='accept' else '拒绝blue分工提议，保留机器人目标且检查仍需完成。'))
        elif choice=='yield':
            self.cost['yields']+=1;start=self.world.tick;baseline=len(self.pending_events)
            for _ in range(CONFIG['yield_limit_ticks']):
                self.world.simulate(1)
                if len(self.pending_events)>baseline:break
            ticks=self.world.tick-start;self.cost['wait_ticks']+=ticks;result.update(wait_ticks=ticks,feedback='实际等待至新公共事件或窗口结束。')
        elif choice in {c['id'] for c in MENU}:
            if choice=='reload_blue':item,target='blue','carrier';self.cost['reloads']+=1
            else:_,item,target=choice.split('_')
            if self.world.at_goal(item,target):result.update(no_op=True,feedback=f'{item}实际已在所选区域{target}，未重复抓放。')
            else:
                execution=self.world.pick_place(item,target,'careful' if item in ('red','green') else 'direct')
                attempted=execution['physical_attempt'];self.cost['physical_attempts']+=int(attempted);self.cost['physical_failures']+=int(attempted and not execution['success'])
                actual=[r for r in ('left','right','inspection','carrier') if (r not in ('inspection','carrier') or item=='blue') and self.world.at_goal(item,r)]
                result.update(execution=execution,valid=execution['success'],feedback=f'物理响应{execution["reason"]}；{item}实际区域{actual}。')
                if attempted and not execution['success']:self.terminated=True;self.termination_reason='physical_failure'
        else:result.update(valid=False,feedback='未知候选未执行。')
        self.cost['invalid']+=int(not result['valid']);self.cost['no_ops']+=int(result['no_op']);self.sync_events()
        self._append(dict(kind='action_feedback',choice=choice,content=result['feedback']))
        if not self.terminated and self.cost['decisions']>=CONFIG['decision_budget']:self.terminated=True;self.termination_reason='budget_exhausted'
        result.update(terminated=self.terminated,termination_reason=self.termination_reason);return copy.deepcopy(result)


def reference(obs):
    ledger=public_ledger(obs['history']);regions=obs['physical_placements'];carrier=obs['physical']['carrier'];motion=obs['motion']
    if 'left' not in regions['red']:return 'request_transport' if not motion['legs'] else 'careful_red_left'
    if motion['active'] is not None:return 'yield'
    if not ledger['check_completed']:
        if not carrier['near']:return 'request_transport' if carrier['far'] else 'yield'
        if 'inspection' not in regions['blue']:return 'place_blue_inspection'
        if not ledger['child_active']:
            near=obs['physical']['presence']['near'] and obs['physical']['presence_motion'] is None
            return 'request_check' if near else 'yield'
        return 'yield'
    if not carrier['far']:
        if ledger['blue_role']=='partner_return' and 'carrier' not in regions['blue']:return 'reload_blue'
        return 'request_return'
    if ledger['blue_role']=='robot' and ledger['goals']['blue'] not in regions['blue']:return 'place_blue_'+ledger['goals']['blue']
    if 'right' not in regions['green']:return 'careful_green_right'
    return 'declare_done'


def terminal_score(ep,state):
    ledger=public_ledger(ep.history);f=state['current_carrier_facts'];cycle=state['cycle']
    # 实际当前支撑与本次返回事件合取，任何旧历史都不能单独作当前履责。
    latest=cycle['legs'][-1] if cycle['legs'] else None
    partner=bool(latest and latest['direction']=='return' and latest['payload_event'] is not None and f['far'] and f['payload_stable'])
    facts=dict(check_completed=ep.service.completed,no_active_child=not ledger['child_active'],red_left=stable_region(state,'red','left'),green_right=stable_region(state,'green','right'),
        carrier_current_far=f['far'] and cycle['active'] is None,blue_role_completed=partner if ledger['blue_role']=='partner_return' else stable_region(state,'blue',ledger['goals']['blue']))
    return dict(facts=facts,task_success=all(facts.values()) and ep.termination_reason=='declared_done')
