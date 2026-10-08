"""仅决定何时重新调用生成式人策略；不选择意图、动作、分工或正确答案。"""
import math


class HumanDecisionSchedule:
    def __init__(self,min_interval_s=4.,max_silence_s=20.):
        if not all(math.isfinite(value) for value in [min_interval_s,max_silence_s]) or min_interval_s<=0 or max_silence_s<min_interval_s:
            raise ValueError('人决策间隔设置无效')
        self.min_interval_s=float(min_interval_s);self.max_silence_s=float(max_silence_s)
        self.last_decision_s=None;self.last_check_s=None;self.previous=None
        self.pending=set();self.last_robot_statement=None;self.seen_context=set()

    def check(self,record,dialogue,private_context):
        time=float(record['time_s'])
        if not math.isfinite(time):raise ValueError('决策检查时间须有限')
        if self.last_check_s is not None and time<self.last_check_s:raise ValueError('决策检查时间不能倒退')
        if any(message['time_s']>time for message in dialogue):raise ValueError('不能读取未来公开交流')
        if any(cue['time_s']>time or not cue['time_s']<=cue.get('delivered_time_s',cue['time_s'])<=time
               for cue in private_context):raise ValueError('不能读取尚未送达的私人情境')
        self.last_check_s=time
        execution=record['human_execution'];receipt=execution.get('last_receipt') or {}
        world=record.get('observable_world',{})
        contacts=tuple(sorted((name,state['robot_hand_contact']) for name,state in world.get('object_contacts',{}).items()))
        relations=world.get('public_relation_summary',{}).get('reference_relations',{})
        supports=tuple(sorted((name,None if info['observed_supported_items'] is None else
            tuple(sorted(item['object_id'] for item in info['observed_supported_items']))) for name,info in relations.items()))
        error=(receipt.get('error'),receipt.get('choice',{}).get('action'),
               receipt.get('choice',{}).get('object_id'),receipt.get('choice',{}).get('destination')) if receipt.get('accepted') is False else None
        state={'owned':(execution.get('held_object'),tuple(sorted(execution.get('carried_objects',[])))),
            'completed':tuple(execution.get('completed_requests',[])),
            'moving':execution.get('motion_in_progress',execution.get('phase')!='idle'),
            'aside':record['human_body_xy'][1]>=.8,'robot_contacts':contacts,'supports':supports,'error':error}
        if self.previous is not None:
            for name,label in [('owned','own_resource_change'),('aside','actual_participation_change'),
                               ('robot_contacts','robot_contact_change'),('supports','observed_support_change')]:
                if state[name]!=self.previous[name]:self.pending.add(label)
            no_op=receipt.get('effect')=='already_at_requested_supported_position'
            if not no_op and (state['completed']!=self.previous['completed'] or
                             (self.previous['moving'] and not state['moving'])):
                self.pending.add('own_execution_update')
            if error is not None and error!=self.previous['error']:self.pending.add('new_execution_rejection')
        self.previous=state
        # 只检查最新机器人表达；持续重复同一确认话语不触发每轮再次推理。
        robot=[message for message in dialogue if message['speaker']=='robot']
        if robot:
            current=(robot[-1]['kind'],robot[-1]['text'])
            if current!=self.last_robot_statement:self.pending.add('new_public_robot_statement')
            self.last_robot_statement=current
        for cue in private_context:
            key=(cue['time_s'],cue['text'])
            if key not in self.seen_context:self.pending.add('new_private_context');self.seen_context.add(key)
        due=self.last_decision_s is None or time-self.last_decision_s>=self.min_interval_s
        reasons=sorted(self.pending)
        if self.last_decision_s is None:reasons=['initial_observation',*reasons]
        elif time-self.last_decision_s>=self.max_silence_s:reasons=[*reasons,'periodic_reconsideration']
        decide=bool(due and reasons)
        if decide:self.last_decision_s=time;self.pending.clear()
        return {'time_s':time,'call_neural_policy':decide,'observed_reasons':reasons,
            'scope':'仅分配策略调用时机；身体持续执行已有模型选择，新意图与当前贡献仍由NN产生。'}
