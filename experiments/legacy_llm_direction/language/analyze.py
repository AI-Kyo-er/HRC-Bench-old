"""只读冻结模型轨迹，报告观察到的行为，不推断模型隐藏状态。"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def analyze(root, output):
    episodes=[json.loads(line) for line in (root/'episodes.jsonl').read_text().splitlines()]
    calls=[json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines()]
    lengths=defaultdict(list)
    errors=Counter()
    requests=Counter()
    stages=defaultdict(lambda:{'calls':0,'completed':0,'parse_errors':0,'invalid_actions':0})
    for call in calls:
        structure=call['case_id'].split('.')[2]
        stage=stages[f"{structure}/{call['view']}/step{call['step']}"]
        stage['calls']+=1
        stage['completed']+=int(call['step_completed'])
        stage['parse_errors']+=int(call['parse_error'] is not None)
        stage['invalid_actions']+=int(call['parsed_action'] is not None and call['parsed_action'] not in call['reference_allowed_actions'])
        lengths[call['view']].append(call['input_tokens'])
        if call['parsed_action'] and call['parsed_action'].get('action')=='request':
            requests[call['case_id'].rsplit('.',1)[-1]]+=1
        if call['parse_error']:
            errors['parse_error']+=1
        elif call['parsed_action'] not in call['reference_allowed_actions']:
            a=call['parsed_action']; allowed=call['reference_allowed_actions']
            if allowed and a.get('item')!=allowed[0].get('item'):
                errors['wrong_item']+=1
            elif allowed and all(x['action']=='yield' for x in allowed) and a['action']!='yield':
                errors['wrong_owner_action']+=1
            elif a['action']=='place' and any(x['action']=='place' for x in allowed) and all(
                    x.get('destination')!=a.get('destination') for x in allowed if x['action']=='place'):
                errors['wrong_destination']+=1
            elif a['action']=='request' and '本轮不需要支撑' in call['messages'][-1]['content']:
                errors['support_request_when_not_needed']+=1
            elif a['action']=='request' and '伙伴暂离' in call['messages'][-1]['content']:
                errors['support_request_when_partner_absent']+=1
            else:
                errors['other_invalid_action']+=1
    executed_requests=Counter()
    for e in episodes:
        executed_requests[e['case_id'].rsplit('.',1)[-1]]+=e['requests']
        for step in range(3):
            stages[f"{e['structure']}/{e['view']}/step{step}"]['assigned_steps']=sum(x['structure']==e['structure'] and x['view']==e['view'] for x in episodes)
    paired=defaultdict(dict)
    for e in episodes:
        paired[e['case_id']][e['view']]=e['episode_completed']
    contingency=Counter(f"history={int(v['full_history'])},summary={int(v['oracle_summary'])}" for v in paired.values())
    result={'decision_stage_breakdown':dict(stages),'paired_episode_contingency':dict(contingency),'observed_error_categories':dict(errors),
            'attempted_requests_by_partner_type':dict(requests),'executed_requests_by_partner_type':dict(executed_requests),
            'invalid_action_ends_current_step':True,'recovery_opportunities_after_invalid':0,
            'input_tokens':{k:{'min':min(v),'max':max(v),'mean':sum(v)/len(v),'calls':len(v)} for k,v in lengths.items()},
            'generation_hit_limit':sum(call['generation_hit_limit'] for call in calls),
            'total_calls':len(calls),'elapsed_generation_seconds':sum(call['seconds'] for call in calls),
            'limitations':['错误类型为可见动作偏差，不能证明隐藏记忆或意图机制。',
                '各view由自身模型动作驱动伙伴轨迹，严格输入长度与轨迹未匹配。',
                'oracle摘要为诊断干预，不是公平方法比较。',
                '若没有request，接受/拒绝轴虽冻结但并未被模型轨迹触发。']}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.root,a.output)
