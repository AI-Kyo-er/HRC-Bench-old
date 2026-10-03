"""独立只读：实际输入/全tick、timing位置匹配、公开错误策略首次选择。"""
import copy
import gzip
import json
from collections import Counter

from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import prefix_digest
from experiments.structure_v7.audit import regions
from experiments.structure_v11.run import RESULT,FREEZE,source_hashes
from experiments.structure_v11.protocol import SYSTEM,candidates,reduce_history,effective_blue_returns,update_events
from experiments.structure_v11.preflight import history_design
from experiments.structure_v11.strategies import STRATEGIES


def first_attempt(rows):
    finish=next(i for i,r in enumerate(rows) if r['result']['choice']=='finish_guidance' and r['result']['valid'])
    prior=[]
    for i,row in enumerate(rows[finish+1:],finish+1):
        choice=row['result']['choice']
        if choice.startswith(('place_blue_','careful_blue_','assisted_blue_')):
            target=reduce_history(row['observation']['history'])['goals']['blue']
            return dict(choice=choice,decision=i+1,target_correct=choice.rsplit('_',1)[1]==target,
                prior_target_feedback=sum(r['result'].get('target_revealing_feedback',False) for r in prior),
                physical_attempt=row['result'].get('execution',{}).get('physical_attempt',False),
                physical_success=row['result'].get('execution',{}).get('success',False))
        prior.append(row)
    return dict(choice=None,target_correct=False,prior_target_feedback=0,physical_attempt=False,physical_success=False)


def episode_audit(case,tokenizer):
    folder=RESULT/'raw/reference'/case['id'];summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text())
    needed={r['before_tick'] for r in rows}|{a['before']['tick'] for a in summary['update_audit']}|{summary['finish_audit']['after']['tick']}
    snapshots={}
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line)
            if state['tick'] in needed:snapshots[state['tick']]=state
    checks=[]
    for i,row in enumerate(rows):
        obs=row['observation'];state=snapshots[row['before_tick']];history=obs['history']
        next_history=rows[i+1]['observation']['history'] if i+1<len(rows) else history
        updates=[e for e in history if e['kind'] in ('update_proposed','proposal_reply')]
        should_have=case['timing']=='before_child' or i>=2
        check=dict(decision=i+1,messages_exact=row['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            physical_exact=obs['physical']['objects']==state['objects'] and obs['physical']['partner_position']==state['partner_position'],
            region_exact=obs['physical_placements']==regions(state),candidate_exact=obs['candidates']==candidates(),
            only_public_keys=set(obs)=={'history','physical','physical_placements','remaining_decisions','candidates'},budget_exact=obs['remaining_decisions']==12-i,
            immutable_history_prefix=next_history[:len(history)]==history,
            feedback_once=i+1==len(rows) or next_history[len(history):].count(dict(kind='action_feedback',choice=row['result']['choice'],content=row['result']['feedback']))==1,
            no_future_update_leak=updates==(update_events(case['proposed_blue'],case['reply']) if should_have else []))
        check['passed']=all(v for k,v in check.items() if k!='decision');checks.append(check)
    injection=summary['update_audit'][0];position=injection['history_start_index']
    delivery_checks=dict(no_physical_step=injection['before']==injection['after']==snapshots[injection['before']['tick']],
        event_block_exact=injection['events']==update_events(case['proposed_blue'],case['reply']),
        correct_actual_arrival_tick=injection['before']['tick']==(3120 if case['timing']=='before_child' else 6900),
        active_child_remains_neutral=not injection['public_before']['active'] or injection['public_after']['goals']['blue']=='neutral',
        other_goals_preserved=all(injection['public_before']['outer'][x]==injection['public_after']['outer'][x] for x in ('red','green')))
    finish=summary['finish_audit'];obs=summary['finish_observation'];finished_state=snapshots[finish['after']['tick']]
    actual_source=ROOT/f"results/structure_v7/raw/reference/B_neutral_{case['initial_blue']}_{case['seed']}_normal/decisions.json"
    old_history=json.loads(actual_source.read_text())[4]['observation']['history']
    checkpoint=dict(finish_matches_tick=finish['before']==finish['after']==finished_state,
        history_matches_prefreeze_design=obs['history']==history_design(old_history,case),
        green_preserved=finish['green_right_before'] and finish['green_right_after'] and all(r['observation']['physical_placements']['green']==['right'] for r in rows[3:]),
        blue_neutral_and_whole_task_unfinished=finish['blue_neutral'] and not finish['global_success_immediately_after_finish'],
        finish_does_not_restate_target=all('goals' not in e and 'destination' not in e for e in obs['history'][-3:]),
        green_done_while_child=summary['green_completed_while_child_active'])
    ids=summary['body_ids'];contacts=contact_audit(folder/'ticks.jsonl.gz',ids['robot'],ids['partner'],ids['objects'].values())
    first=first_attempt(rows)
    passed=all(c['passed'] for c in checks) and all(delivery_checks.values()) and all(checkpoint.values()) and contacts==summary['contact_audit_raw_ticks'] and contacts['zero_record_passed'] and contacts['all_missing_distance_records']==0 and first['target_correct'] and first['physical_success'] and first['prior_target_feedback']==0
    return dict(id=case['id'],passed=passed,decisions=checks,update_delivery=delivery_checks,update_start_index=position,checkpoint=checkpoint,
        first_return=first,contacts=contacts,finish_tokens=len(tokenizer.apply_chat_template(rows[-1]['messages'],tokenize=True,add_generation_prompt=True)),
        finish_characters=sum(len(m['content']) for m in rows[-1]['messages']),
        decisions_sha256=sha(folder/'decisions.json'),ticks_gzip_sha256=sha(folder/'ticks.jsonl.gz'),
        prefix_canonical_sha256=prefix_digest(folder/'ticks.jsonl.gz',finish['after']['tick']),
        full_trace_canonical_sha256=prefix_digest(folder/'ticks.jsonl.gz',summary['final_state']['tick']))


def main():
    from transformers import AutoTokenizer
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==source_hashes() and frozen['packages']==versions() and frozen['assets_sha256']==asset_hashes()
    assert frozen['design_audit_sha256']==sha(RESULT/'prefreeze_design_audit.json')
    assert frozen['tokenizer_assets_sha256']=={n:sha(ROOT/'models/Qwen2.5-14B-Instruct'/n) for n in frozen['tokenizer_assets_sha256']}
    tokenizer=AutoTokenizer.from_pretrained(ROOT/'models/Qwen2.5-14B-Instruct',local_files_only=True)
    audited=[episode_audit(case,tokenizer) for case in frozen['cases']];pairs=[];strategies=[]
    summaries={c['id']:json.loads((RESULT/'raw/reference'/c['id']/'summary.json').read_text()) for c in frozen['cases']}
    for seed in (60,61):
        for reply in ('accepted','rejected'):
            for initial in ('left','right'):
                pair=[c for c in frozen['cases'] if c['seed']==seed and c['reply']==reply and c['initial_blue']==initial]
                ss=[summaries[c['id']] for c in pair];aa=[next(a for a in audited if a['id']==c['id']) for c in pair]
                histories=[s['finish_observation']['history'] for s in ss]
                without=[[e for e in h if e['kind'] not in ('update_proposed','proposal_reply')] for h in histories]
                blocks=[[e for e in h if e['kind'] in ('update_proposed','proposal_reply')] for h in histories]
                nohist=[{k:v for k,v in s['finish_observation'].items() if k!='history'} for s in ss]
                checks=dict(checkpoint_exact=ss[0]['finish_audit']['after']==ss[1]['finish_audit']['after'],full_prefix_exact=aa[0]['prefix_canonical_sha256']==aa[1]['prefix_canonical_sha256'],
                    complete_physical_trace_exact=aa[0]['full_trace_canonical_sha256']==aa[1]['full_trace_canonical_sha256'],no_history_input_exact=nohist[0]==nohist[1],
                    nonupdate_events_exact=without[0]==without[1],update_block_exact=blocks[0]==blocks[1],
                    event_multiset_exact=Counter(json.dumps(e,sort_keys=True,ensure_ascii=False) for e in histories[0])==Counter(json.dumps(e,sort_keys=True,ensure_ascii=False) for e in histories[1]),
                    fifteen_events=all(len(h)==15 for h in histories),tokens_equal=aa[0]['finish_tokens']==aa[1]['finish_tokens'],characters_equal=aa[0]['finish_characters']==aa[1]['finish_characters'],budget_both_eight=all(o['remaining_decisions']==8 for o in nohist))
                pairs.append(dict(seed=seed,reply=reply,initial_blue=initial,ids=[c['id'] for c in pair],checks=checks,passed=all(checks.values())))
    response_pairs=[]
    for seed in (60,61):
        for timing in ('before_child','during_child'):
            for initial in ('left','right'):
                ss=[summaries[c['id']] for c in frozen['cases'] if c['seed']==seed and c['timing']==timing and c['initial_blue']==initial]
                allowed=[effective_blue_returns(s['finish_observation']) for s in ss]
                response_pairs.append(dict(seed=seed,timing=timing,initial_blue=initial,effective_sets=allowed,
                    disjoint=not set(allowed[0])&set(allowed[1]),same_finish_physical=ss[0]['finish_audit']['after']==ss[1]['finish_audit']['after']))
    for case in frozen['cases']:
        obs=summaries[case['id']]['finish_observation'];allowed=effective_blue_returns(obs)
        for name,policy in STRATEGIES.items():
            choice=f"place_blue_{policy(obs['history'])}"
            strategies.append(dict(id=case['id'],timing=case['timing'],reply=case['reply'],initial_blue=case['initial_blue'],seed=case['seed'],strategy=name,
                choice=choice,effective_choices=allowed,first_return_match=choice in allowed,physical_execution=False,whole_episode_result=None))
    save(RESULT/'public_strategy_diagnostic.json',dict(rows=strategies,by_strategy={name:dict(total=16,first_return_match=sum(r['first_return_match'] for r in strategies if r['strategy']==name),
        by_timing={timing:dict(total=8,matched=sum(r['first_return_match'] for r in strategies if r['strategy']==name and r['timing']==timing)) for timing in ('before_child','during_child')}) for name in STRATEGIES},
        interpretation='公开history策略对实际finish后的首次返回有效集合离线匹配，不执行错误动作，不是整段episode结果。',
        source_sha256=sha(ROOT/'experiments/structure_v11/strategies.py')))
    correct_public_ledger_matches_all=all(r['first_return_match'] for r in strategies if r['strategy']=='last_accepted_outer')
    report=dict(all_passed=all(a['passed'] for a in audited) and all(p['passed'] for p in pairs) and all(p['disjoint'] and p['same_finish_physical'] for p in response_pairs) and correct_public_ledger_matches_all,
        total_episodes=16,total_decisions=sum(len(a['decisions']) for a in audited),episodes=audited,timing_pairs=pairs,response_pairs=response_pairs,
        freeze_sha256=sha(FREEZE),runtime_source_sha256=source_hashes(),postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_v11/audit.py'),
        correct_public_ledger_matches_all=correct_public_ledger_matches_all,model_calls=0,interpretation='timing移动同事件块亦改变新近程度；早期决策历史不等长。单层脚本回应规则可行性，非纯scope因果/模型/组合泛化。')
    save(RESULT/'input_and_pair_audit.json',report);assert report['all_passed']
    print('v11真实16例/80决策/八组timing审计全部通过',flush=True)


if __name__=='__main__':main()
