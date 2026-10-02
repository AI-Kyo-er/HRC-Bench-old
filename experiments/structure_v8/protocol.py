"""共同投递/接手任务；响应策略只读公开约定，保守参照为固定独立算法。"""
import copy
import json

from experiments.physical.protocol import candidates
from experiments.structure_v8.world_v2 import CONFIG

SYSTEM = '''持续共同任务：伙伴电机自主运输blue至公开交接位置，你负责red到left及交付后接blue到left；green未分配，保留。
依据原始公开已接受先后/并行约定组织动作。伙伴运输每个物理tick自主推进，yield只等待实际稳定交付，不启动或加速运输。
候选为全部20通用能力，当前错误/不可执行动作也保留，拒绝计决策成本并反馈。place直接抓放，careful绕行，assisted需已接受协助，request_clear只请求清道。
交付历史事件来自真实载台/blue位姿、速度与支持接触共同满足，接走blue后保留已发生事件。
只输出{"choice":"候选ID"}。
'''


def cases():
    return [dict(id=f'A_delivery_{condition}_{seed}', seed=seed, agreement=agreement, policy=policy, step_budget=8)
            for seed in (70, 71)
            for condition, agreement, policy in (
                ('exclusive_response', 'exclusive', 'responsive'),
                ('shared_wait', 'shared', 'conservative'),
                ('shared_overlap', 'shared', 'responsive'))]


def reduce_history(history):
    goals = {}
    allow_overlap = False
    for event in history:
        if event['kind'] == 'accepted_goals':
            goals = dict(event['goals'])
        elif event['kind'] == 'accepted_sequence':
            allow_overlap = event['allow_overlap']
    return dict(goals=goals, allow_overlap=allow_overlap)


class Episode:
    def __init__(self, case, world):
        self.case, self.world = case, world
        shared = case['agreement'] == 'shared'
        self.history = [
            dict(kind='background_source', content='脚本预置已共同接受的分工/许可，非模型亲自协商。'),
            dict(kind='accepted_goals', goals={'red': 'left', 'blue': 'left'}, content='伙伴负责实物blue投递，机器人整理red并接blue；green未分配应保留。'),
            dict(kind='accepted_sequence', allow_overlap=shared,
                 content='已接受共享许可：伙伴投递过程中机器人可整理red；稳定交付后接blue。' if shared else
                         '已接受先后约定：伙伴稳定交付blue之前机器人等待，随后整理red并接blue。')]
        self.cost = dict(decisions=0, invalid=0, yields=0, requests=0, wait_ticks=0, physical_attempts=0, physical_failures=0)
        self.initial_state = copy.deepcopy(world.state())
        self.robot_intervals = []
        self.executions = []
        world.start_delivery()
        self.checkpoint = copy.deepcopy(world.state())

    def observation(self):
        state = self.world.state()
        return copy.deepcopy(dict(history=self.history,
            physical=dict(objects=state['objects'], carrier_position=state['partner_position'],
                          carrier_velocity=state['partner_velocity'], direct_path_blocked=self.world.direct_blocked()),
            physical_placements={i:[t for t in ('left','right') if self.world.at_goal(i,t)] for i in ('red','blue','green')},
            delivery_event=state['delivery_event'],
            delivery_region=dict(carrier_center=[.65,0,CONFIG['carrier_center_start'][2]], blue_relative_position=[0,0,.027],
                                 description='承载接触及真实相对位置/速度稳定后形成交付事件。'),
            remaining_decisions=self.case['step_budget']-self.cost['decisions'], candidates=candidates()))

    def messages(self):
        return [{'role':'system','content':SYSTEM}, {'role':'user','content':json.dumps(self.observation(),ensure_ascii=False)}]

    def success(self):
        goals = reduce_history(self.history)['goals']
        return self.world.delivery_event is not None and all(self.world.at_goal(i,t) for i,t in goals.items())

    def act(self, choice):
        current = reduce_history(self.history)
        self.cost['decisions'] += 1
        result = dict(choice=choice, valid=True)
        if choice == 'yield':
            self.cost['yields'] += 1
            result['wait'] = self.world.wait_delivery()
            self.cost['wait_ticks'] += result['wait']['ticks']
            result['feedback'] = '已观察到实际稳定交付。' if result['wait']['success'] else '等待预算耗尽，尚未实际稳定交付。'
        elif choice == 'request_clear':
            self.cost['requests'] += 1
            result['feedback'] = '载台按既定自主轨迹运输；请求不启动/加速/取消运输，不授予额外搬运能力。'
        elif choice in {c['id'] for c in candidates()}:
            mode, item, target = choice.split('_')
            if item not in current['goals']:
                result.update(valid=False, feedback='green未分配任务，应保留其物理进度。')
            elif self.world.delivery_event is None and (item == 'blue' or not current['allow_overlap']):
                result.update(valid=False, feedback='已接受的交付/先后约定要求先等实际稳定交付；此次抓放未执行。')
            elif target != current['goals'][item]:
                result.update(valid=False, feedback=f'与公开约定冲突：{item}应到{current["goals"][item]}。')
            elif self.world.at_goal(item, target):
                result.update(valid=False, feedback='该物品已在约定区域，继续其他分工。')
            elif mode == 'assisted':
                result.update(valid=False, feedback='没有已接受清道协助。')
            else:
                before = self.world.tick
                execution = self.world.pick_place(item,target,'careful' if mode=='careful' else 'direct')
                self.executions.append(execution)
                self.robot_intervals.append(dict(item=item,start=before,end=self.world.tick))
                result.update(execution=execution, feedback=execution['reason'])
                self.cost['physical_attempts'] += int(execution['physical_attempt'])
                self.cost['physical_failures'] += int(execution['physical_attempt'] and not execution['success'])
        else:
            result.update(valid=False,feedback='未知候选。')
        self.cost['invalid'] += int(not result['valid'])
        if self.world.delivery_event is not None and not any(e['kind']=='physical_delivery_occurred' for e in self.history):
            self.history.append(dict(kind='physical_delivery_occurred',event=copy.deepcopy(self.world.delivery_event),
                                     content='实际交付事件已发生；接走blue后此历史仍有效。'))
        self.history.append(dict(kind='action_feedback', choice=choice, content=result['feedback']))
        result['success']=self.success()
        return copy.deepcopy(result)


def reference(observation, policy='responsive'):
    """policy是独立参照算法选择；协议条件仅通过公开history读取。"""
    current = reduce_history(observation['history'])
    delivered = observation['delivery_event'] is not None
    red_done = current['goals']['red'] in observation['physical_placements']['red']
    if not delivered:
        if policy=='conservative' or not current['allow_overlap'] or red_done:
            return 'yield'
        return 'careful_red_left'
    if not red_done:
        return 'careful_red_left'
    if current['goals']['blue'] not in observation['physical_placements']['blue']:
        return 'place_blue_left'
    raise ValueError('公开共同任务已完成。')
