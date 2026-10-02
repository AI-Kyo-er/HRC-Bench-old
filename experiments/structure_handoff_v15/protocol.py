"""独立伙伴交还协议：沿v11机械路径，伙伴公开交还也可终止child。"""
import copy
import json

from experiments.structure_v5.protocol import candidates as old_candidates

CHILD_CONTENT='已接受blue局部指导：暂存neutral，实际检查通过且伙伴已撤离后，伙伴明确交还或机器人finish_guidance均可终止，恢复当时有效外层blue约定；red/green继续原约定。'

SYSTEM = '''你控制持续桌面任务。只输出{"choice":"候选ID"}。
公开历史中的已接受约定由脚本共同背景预置，不表示你亲自协商。
局部blue指导要求真实暂存到neutral检查盘；伙伴进入检查后先yield让其撤离。
外层blue投递调整只有对应提议被接受才生效，拒绝保留原约定。指导期间的已接受外层调整不取消neutral检查，终止指导后按最新有效外层约定投递；red/green约定及物理进度保留。
stage_blue_neutral执行上述暂存。局部指导活动且实际检查通过、伙伴已撤离时，伙伴公开交还blue即终止局部指导并恢复当时有效外层blue约定，不移动物品；不需机器人再finish_guidance。机器人也可在满足检查条件时用finish_guidance主动终止；已终止后重复finish_guidance无效。red/green约定与已实现进度保留。
place直接抓放；careful绕行；assisted需已接受清道协助；request_clear只求清道；yield让行，可合法但不推进物品。
全部22候选是公开通用能力集合，包含当前错误或不可执行动作，拒绝与额外动作计决策成本并提供反馈。
依据公开原始历史和真实区域继续任务，自主选择尚未满足约定的物品。
输出格式：{"choice":"候选ID"}。
'''


def candidates(reverse=False):
    menu = old_candidates() + [{'id': 'stage_blue_neutral', 'meaning': '真实抓放blue到独立neutral检查盘，触发伙伴脚本检查'}]
    return list(reversed(menu)) if reverse else menu


def cases():
    return [dict(id=f'B_handoff_{timing}_{reply}_{initial}_{seed}',timing=timing,reply=reply,
                 initial_blue=initial,proposed_blue='right' if initial=='left' else 'left',
                 seed=seed,reverse_menu=False,step_budget=12)
            for seed in (60,61) for timing in ('before_child','during_child')
            for reply in ('accepted','rejected') for initial in ('left','right')]


def update_events(proposed,reply,proposal_id='u1'):
    return [dict(kind='update_proposed',proposal_id=proposal_id,item='blue',destination=proposed,
                 content='只调整blue检查结束后的外层投递；neutral检查与red/green约定不变。'),
            dict(kind='proposal_reply',proposal_id=proposal_id,decision='accept' if reply=='accepted' else 'reject',
                 content='对该提议：'+('接受。' if reply=='accepted' else '拒绝。'))]


def reduce_history(history):
    outer,goals,pending={},{},{}
    active=checked=must_yield=ended=granted=False
    seen=set()
    for event in history:
        kind=event['kind']
        if kind=='accepted_outer':
            outer=dict(event['goals']);goals=dict(outer)
        elif kind=='update_proposed':
            ident=event['proposal_id']
            if ident in seen or event['item']!='blue' or event['destination'] not in ('left','right'):
                raise ValueError('外层投递提议ID/物品/目标无效。')
            seen.add(ident);pending[ident]=event['destination']
        elif kind=='proposal_reply':
            ident=event['proposal_id']
            if ident not in pending or event['decision'] not in ('accept','reject'):
                raise ValueError('回应须绑定尚未回应的公开提议。')
            destination=pending.pop(ident)
            if event['decision']=='accept':
                outer['blue']=destination
                if not active:goals['blue']=destination
        elif kind=='accepted_child':
            active=True;checked=False;ended=False;goals['blue']='neutral'
        elif kind=='inspection_started':must_yield=True
        elif kind=='partner_released':
            must_yield=False;granted=event['by']=='request_clear'
        elif kind=='local_check_passed':checked=True
        elif kind=='child_finished':active=False;ended=True
        elif kind=='outer_resumed':goals['blue']=outer['blue']
        elif kind=='partner_handoff':
            if not active or not checked or must_yield:raise ValueError('公开交还需活动指导、已通过检查且已撤离。')
            active=False;ended=True;goals['blue']=outer['blue']
    return dict(outer=outer,goals=goals,active=active,checked=checked,must_yield=must_yield,
                ended=ended,granted=granted,pending=pending)


class Episode:
    def __init__(self, case, world):
        self.case, self.world = case, world
        self.update_injected=False
        self.update_audit=[]
        self.history = [
            {'kind': 'background_source', 'content': '脚本预置初始共同接受背景，非模型协商。'},
            {'kind': 'accepted_outer', 'goals': {'red': 'left', 'blue': case['initial_blue'], 'green': 'right'},
             'content': '已共同接受外层目标，允许自主物品顺序。'}]
        self.prefix = world.pick_place('red', 'left', 'direct')
        if not self.prefix['success']:
            raise RuntimeError('公共red前缀失败。')
        self.history.append({'kind':'prefix_action','content':'red已真实放到left并停车。'})
        if case['timing']=='before_child':self._inject_update()
        self.history.append({'kind':'accepted_child','content':CHILD_CONTENT})
        self.cost = dict(decisions=0, invalid=0, requests=0, yields=0, finishes=0,
                         physical_attempts=0, physical_failures=0, target_corrections=0, blue_target_corrections=0)
        self.finish_audit = None
        self.handoff_audit = None
        self.partner_handoffs = 0
        self.rejected_handoffs = 0
        self.first_blue_return_attempt = None
        self.pre_first_blue_actions = []

    def _inject_update(self):
        if self.update_injected:raise RuntimeError('更新事件块只能注入一次。')
        before=copy.deepcopy(self.world.state())
        public_before=reduce_history(self.history)
        block=update_events(self.case['proposed_blue'],self.case['reply'])
        self.history.extend(copy.deepcopy(block));self.update_injected=True
        self.update_audit.append(dict(events=block,before=before,after=copy.deepcopy(self.world.state()),
            public_before=public_before,public_after=reduce_history(self.history),history_start_index=len(self.history)-2))

    def observation(self):
        state = self.world.state()
        return copy.deepcopy({'history': self.history,
            'physical': {'objects': state['objects'], 'partner_position': state['partner_position'],
                         'direct_path_blocked': self.world.direct_blocked()},
            'physical_placements': {item: [target for target in ('left', 'right', 'neutral')
                                         if (target != 'neutral' or item == 'blue') and self.world.at_goal(item, target)]
                                    for item in ('red', 'blue', 'green')},
            'remaining_decisions': self.case['step_budget'] - self.cost['decisions'],
            'candidates': candidates(self.case['reverse_menu'])})

    def messages(self):
        return [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': json.dumps(self.observation(), ensure_ascii=False)}]

    def success(self):
        current = reduce_history(self.history)
        return current['ended'] and all(self.world.at_goal(i, t) for i, t in current['outer'].items())

    def partner_handoff(self):
        """公开伙伴事件；资格不要求green完成，不计机器人决策或物理tick。"""
        before=copy.deepcopy(self.world.state());current=reduce_history(self.history)
        if not current['active'] or not current['checked'] or current['must_yield'] or self.world.direct_blocked():
            self.rejected_handoffs+=1
            result=dict(valid=False,feedback='伙伴交还未生效：没有活动指导、检查未通过或伙伴尚未撤离。')
            self.history.append(dict(kind='partner_handoff_rejected',content=result['feedback']))
            assert before==self.world.state()
            return result
        event=dict(kind='partner_handoff',content='局部检查已结束，现在交还blue，按当前有效外层约定继续。')
        green_before=self.world.at_goal('green','right')
        self.history.append(event);self.partner_handoffs+=1
        self.handoff_audit=dict(event=event,before=before,after=copy.deepcopy(self.world.state()),
            green_right_before=green_before,green_right_after=self.world.at_goal('green','right'),
            public_before=current,public_after=reduce_history(self.history),
            robot_decisions_before=self.cost['decisions'],robot_decisions_after=self.cost['decisions'],
            history_index=len(self.history)-1,global_success_immediately_after_handoff=self.success())
        return dict(valid=True,feedback=event['content'])

    def act(self, choice):
        self.cost['decisions'] += 1
        current = reduce_history(self.history)
        result = {'choice': choice, 'valid': True, 'target_revealing_feedback': False}
        first = current['ended'] and self.first_blue_return_attempt is None
        blue_return = choice in {f'{mode}_blue_{target}' for mode in ('place', 'careful', 'assisted') for target in ('left', 'right')}
        corrections_before = self.cost['blue_target_corrections']
        if choice == 'finish_guidance':
            self.cost['finishes'] += 1
            if not current['active'] or not current['checked'] or not self.world.at_goal('blue', 'neutral'):
                result.update(valid=False, feedback='当前局部检查未满足终止条件，或没有活动的局部指导。')
            else:
                before = copy.deepcopy(self.world.state())
                green_before = self.world.at_goal('green', 'right')
                self.history.extend([
                    {'kind': 'child_finished', 'content': '局部检查完成，当前指导明确终止。'},
                    {'kind': 'outer_resumed', 'content': '恢复当时有效外层blue约定；其他分工和已实现物理进度保留。'}])
                self.finish_audit = dict(before=before, after=copy.deepcopy(self.world.state()),
                    green_right_before=green_before, green_right_after=self.world.at_goal('green', 'right'),
                    blue_neutral=self.world.at_goal('blue', 'neutral'),
                    active_after=reduce_history(self.history)['active'],
                    global_success_immediately_after_finish=self.success())
                result['feedback'] = '局部指导已终止，请继续此前外层约定。'
        elif choice in ('yield', 'request_clear'):
            self.cost['yields' if choice == 'yield' else 'requests'] += 1
            if self.world.direct_blocked() and choice == 'yield' and current['must_yield']:
                result['partner_motion'] = self.world.move_partner(False)
                self.history.append({'kind': 'partner_released', 'by': choice, 'content': '伙伴实际撤离共享通道。'})
                if current['active'] and self.world.at_goal('blue', 'neutral'):
                    self.history.append({'kind': 'local_check_passed', 'content': '伙伴脚本依据实际blue在neutral的位姿完成检查，可终止指导。'})
                result['feedback'] = '伙伴已撤离，现有物品约定继续有效。'
            else:
                result['feedback'] = '检查顺序要求先yield。' if current['must_yield'] else '让行/重复请求合法但不推进物品。'
        elif choice == 'stage_blue_neutral':
            if not current['active'] or current['must_yield'] or self.world.at_goal('blue', 'neutral'):
                result.update(valid=False, feedback='当前无需或暂不能再次暂存blue。')
            else:
                execution = self.world.pick_place('blue', 'neutral', 'direct')
                self._execution(result, execution)
                if execution['success']:
                    result['partner_motion'] = self.world.move_partner(True)
                    self.history.append({'kind': 'inspection_started', 'content': '伙伴真实进入共享通道进行脚本检查，已接受顺序要求先yield令其撤离。'})
        elif choice in {c['id'] for c in candidates()}:
            mode, item, target = choice.split('_')
            if current['must_yield']:
                result.update(valid=False, feedback='已接受检查顺序要求下一抓放前先yield。')
            elif target != current['goals'][item]:
                result.update(valid=False, target_revealing_feedback=True,
                              feedback=f'与已接受目标冲突：{item}应到{current["goals"][item]}。')
                self.cost['target_corrections'] += 1
                self.cost['blue_target_corrections'] += int(item == 'blue')
            elif self.world.at_goal(item, target):
                result.update(valid=False, feedback='该物品目标已满足，请推进其他约定。')
            elif mode == 'assisted' and not current['granted']:
                result.update(valid=False, feedback='当前没有已接受清道协助。')
            else:
                self._execution(result, self.world.pick_place(item, target, 'careful' if mode == 'careful' else 'direct'))
        else:
            result.update(valid=False, feedback='未知候选，请按公开菜单重试。')
        self.cost['invalid'] += int(not result['valid'])
        if first:
            if blue_return:
                self.first_blue_return_attempt = dict(choice=choice, decision=self.cost['decisions'],
                    prior_target_corrections=corrections_before,
                    target_correct=choice.rsplit('_', 1)[1] == current['goals']['blue'],
                    valid=result['valid'], physical_attempt=result.get('execution', {}).get('physical_attempt', False),
                    placement_success=result.get('execution', {}).get('success', False),
                    feedback=result['feedback'], target_revealing_feedback=result['target_revealing_feedback'])
            else:
                self.pre_first_blue_actions.append(dict(choice=choice,
                    target_revealing_feedback=result['target_revealing_feedback']))
        self.history.append({'kind': 'action_feedback', 'choice': choice, 'content': result['feedback']})
        if self.case['timing']=='during_child' and not self.update_injected and choice=='yield' and reduce_history(self.history)['checked']:
            self._inject_update()
        result['success'] = self.success()
        return copy.deepcopy(result)

    def _execution(self, result, execution):
        result['execution'] = execution
        self.cost['physical_attempts'] += int(execution['physical_attempt'])
        self.cost['physical_failures'] += int(execution['physical_attempt'] and not execution['success'])
        result['feedback'] = execution['reason']


def reference(observation):
    current = reduce_history(observation['history'])
    regions = observation['physical_placements']
    if current['must_yield']:
        return 'yield'
    if current['active']:
        if 'neutral' not in regions['blue']:
            return 'stage_blue_neutral'
        if 'right' not in regions['green']:
            return 'place_green_right'
        return 'finish_guidance'
    for item in ('blue', 'green', 'red'):
        if current['goals'][item] not in regions[item]:
            return f'place_{item}_{current["goals"][item]}'
    raise ValueError('公开目标无剩余动作。')


def effective_blue_returns(observation):
    """仅供审计/评分；从公开历史推导，不添加到观察。共同合法no-op另行保留。"""
    current = reduce_history(observation['history'])
    if not current['ended'] or current['must_yield'] or observation['physical']['direct_path_blocked']:
        return []
    target = current['goals']['blue']
    return [f'{mode}_blue_{target}' for mode in ('place', 'careful')]
