"""旧控制证据核验后冻结16例；规则只读公开原始history，无神经调用。"""
import argparse
import copy
import json
from pathlib import Path

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import keyframe, prefix_digest
from experiments.structure_v7.world import NeutralWorld
from experiments.structure_v11.protocol import Episode, cases, reference, reduce_history, effective_blue_returns, SYSTEM

RESULT = ROOT / 'results/structure_v11'
FREEZE = ROOT / 'experiments/structure_v11/cases/reference_freeze.json'
SOURCES = ['experiments/physical/world.py', 'experiments/physical/protocol.py',
    'experiments/physical/run.py', 'experiments/physical_v3_2/world.py',
    'experiments/structure_v5/world.py', 'experiments/structure_v5/world_v2.py',
    'experiments/structure_v5/world_v3.py', 'experiments/structure_v5/audit.py',
    'experiments/structure_v5/run.py', 'experiments/structure_v7/world.py',
    'experiments/structure_v7/controls.py', 'experiments/structure_v11/protocol.py',
    'experiments/structure_v11/run.py','experiments/structure_v11/preflight.py','experiments/structure_v5/protocol.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def freeze():
    from experiments.structure_v11.preflight import design_audit
    if FREEZE.exists():raise RuntimeError('禁止覆盖冻结。')
    old_freeze=ROOT/'experiments/structure_v7/cases/reference_freeze.json'
    old=json.loads(old_freeze.read_text())
    if old['source_sha256']!={n:sha(ROOT/n) for n in old['source_sha256']}:raise RuntimeError('旧控制依赖源码变化。')
    old_control=ROOT/'results/structure_v7/control_summary.json'
    control=json.loads(old_control.read_text())
    if not control['all_passed'] or sha(old_control)!=old['control_summary_sha256']:raise RuntimeError('旧neutral控制证据不一致。')
    design=design_audit();save(RESULT/'prefreeze_design_audit.json',design)
    if not design['all_passed']:raise RuntimeError('设计匹配未通过。')
    assets=asset_hashes();model=ROOT/'models/Qwen2.5-14B-Instruct'
    tokenizer_assets={n:sha(model/n) for n in ('tokenizer.json','tokenizer_config.json','config.json','vocab.json','merges.txt')}
    save(FREEZE,dict(version='structure-v11-outer-update-reference-v1',cases=cases(),source_sha256=source_hashes(),
        packages=versions(),assets_sha256=assets,system=SYSTEM,candidate_count=22,
        reused_v7_control=dict(freeze_sha256=sha(old_freeze),control_summary_sha256=sha(old_control),geometric_control_unchanged=True),
        design_audit_sha256=sha(RESULT/'prefreeze_design_audit.json'),tokenizer_assets_sha256=tokenizer_assets,
        proposal_events_cost='两个外生公开事件，不消耗机器人决策或物理tick；实际到达位置/时刻单列，非真人交流延迟模型。',
        scoring='finish后首次blue放置尝试包含错误目标拒绝；公开错误策略只离线匹配有效集合，不执行或声称整段失败。',
        interpretation='16脚本约定规则参考，序列位置与新近程度同时变化，单层临时指导、无模型/组合泛化/纯scope因果。'))
    print('v11冻结',sha(FREEZE),'16case',flush=True)


def rollout(case, folder):
    folder.mkdir(parents=True)
    world = NeutralWorld(case['seed'], trace_path=folder / 'ticks.jsonl.gz')
    rows = []
    try:
        episode = Episode(case, world)
        rendered = case['seed']==60 and case['initial_blue']=='left' and case['reply']=='accepted'
        if rendered:
            keyframe(world, folder / 'frames')
        finish_observation = None
        for _ in range(case['step_budget']):
            if episode.success():
                break
            observation = episode.observation()
            messages = episode.messages()
            assert json.loads(messages[1]['content']) == json.loads(json.dumps(observation))
            choice = reference(observation)
            before_tick = world.tick
            result = episode.act(choice)
            rows.append(dict(observation=observation, messages=messages,
                prediction={'response': json.dumps({'choice': choice}), 'policy': 'public_history_reference'},
                result=result, before_tick=before_tick, after_tick=world.tick))
            if choice == 'finish_guidance' and result['valid']:
                finish_observation = episode.observation()
            print(case['id'], len(rows), choice, result['feedback'], flush=True)
            if rendered:
                keyframe(world, folder / 'frames')
        finish = episode.finish_audit
        first = episode.first_blue_return_attempt
        summary = dict(case=case, success=episode.success(), cost=episode.cost, prefix_execution=episode.prefix,
            final_state=world.state(),update_audit=copy.deepcopy(episode.update_audit),
            final_public_reduction_for_audit=reduce_history(episode.history),finish_audit=finish, finish_observation=finish_observation,
            first_blue_return_attempt=first, pre_first_blue_actions=episode.pre_first_blue_actions,
            first_blue_attempt_correct_without_prior_target_feedback=bool(first and first['target_correct'] and first['prior_target_corrections'] == 0),
            first_blue_placement_success_without_prior_target_feedback=bool(first and first['placement_success'] and first['prior_target_corrections'] == 0),
            effective_blue_return_actions=effective_blue_returns(finish_observation) if finish_observation else [],
            robot_partner_online=copy.deepcopy(world.contact_audit), object_partner_online=copy.deepcopy(world.object_partner_audit),
            body_ids=dict(robot=world.robot, partner=world.partner, objects=dict(world.objects)),
            green_completed_while_child_active=any(r['result']['choice'] == 'place_green_right' and reduce_history(r['observation']['history'])['active'] and r['result'].get('execution', {}).get('success') for r in rows))
        summary['passed'] = bool(summary['success'] and finish and finish['before'] == finish['after'] and
            finish['green_right_before'] and finish['green_right_after'] and finish['blue_neutral'] and not finish['active_after'] and
            not finish['global_success_immediately_after_finish'] and summary['green_completed_while_child_active'] and
            summary['first_blue_placement_success_without_prior_target_feedback'])
        save(folder / 'decisions.json', rows)
    except Exception as exc:
        save(folder/'failure.json',dict(case=case,error=repr(exc),state=world.state(),completed_decisions=rows,source_sha256=source_hashes()))
        save(folder/'decisions.json',rows)
        raise
    finally:
        world.close()
    ids = summary['body_ids']
    audit = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
    assert audit['robot_partner']['ticks'] == summary['robot_partner_online']['robot_partner_ticks']
    assert audit['object_partner']['ticks'] == summary['object_partner_online']['ticks']
    assert audit['total_ticks'] == summary['robot_partner_online']['total_ticks']
    summary['contact_audit_raw_ticks'] = audit
    summary['prefix_to_finish_trace_sha256'] = prefix_digest(folder / 'ticks.jsonl.gz', finish['after']['tick']) if finish else None
    summary['passed'] = summary['passed'] and len(summary['update_audit'])==1 and all(a['before']==a['after'] for a in summary['update_audit']) and audit['zero_record_passed'] and audit['all_missing_distance_records'] == 0
    save(folder / 'summary.json', summary)
    return summary


def run():
    frozen = json.loads(FREEZE.read_text())
    if frozen['source_sha256'] != source_hashes() or frozen['packages'] != versions() or frozen['assets_sha256'] != asset_hashes():
        raise RuntimeError('环境/源码与冻结不一致。')
    output = RESULT / 'raw/reference'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆写结果。')
    rows = [rollout(c, output / c['id']) for c in frozen['cases']]
    pairs=[]
    for seed in (60,61):
        for reply in ('accepted','rejected'):
            for initial in ('left','right'):
                pair=[r for r in rows if r['case']['seed']==seed and r['case']['reply']==reply and r['case']['initial_blue']==initial]
                nohistory=[{k:v for k,v in r['finish_observation'].items() if k!='history'} for r in pair]
                check=dict(seed=seed,reply=reply,initial_blue=initial,ids=[r['case']['id'] for r in pair],
                    finish_checkpoint_exact=pair[0]['finish_audit']['after']==pair[1]['finish_audit']['after'],
                    full_prefix_exact=pair[0]['prefix_to_finish_trace_sha256']==pair[1]['prefix_to_finish_trace_sha256'],
                    input_without_history_exact=nohistory[0]==nohistory[1],
                    primitive_choices_exact=[r['result']['choice'] for r in json.loads((output/pair[0]['case']['id']/'decisions.json').read_text())]==[r['result']['choice'] for r in json.loads((output/pair[1]['case']['id']/'decisions.json').read_text())])
                check['passed']=all(check[k] for k in ('finish_checkpoint_exact','full_prefix_exact','input_without_history_exact','primitive_choices_exact'))
                pairs.append(check)
    summary=dict(version=frozen['version'],total=len(rows),passed=sum(r['passed'] for r in rows),success=sum(r['success'] for r in rows),
        first_blue_attempt_correct_without_prior_target_feedback=sum(r['first_blue_attempt_correct_without_prior_target_feedback'] for r in rows),
        first_blue_placement_success_without_prior_target_feedback=sum(r['first_blue_placement_success_without_prior_target_feedback'] for r in rows),
        total_ticks=sum(r['contact_audit_raw_ticks']['total_ticks'] for r in rows),
        robot_partner_ticks=sum(r['contact_audit_raw_ticks']['robot_partner']['ticks'] for r in rows),
        object_partner_ticks=sum(r['contact_audit_raw_ticks']['object_partner']['ticks'] for r in rows),pairs=pairs,
        cost={k:sum(r['cost'][k] for r in rows) for k in rows[0]['cost']},exogenous_update_events=2*len(rows),
        freeze_sha256=sha(FREEZE),source_sha256=source_hashes(),interpretation=frozen['interpretation'])
    assert len(rows)==16
    assert sum('place_blue_left' in r['effective_blue_return_actions'] for r in rows)==8
    assert sum('place_blue_right' in r['effective_blue_return_actions'] for r in rows)==8

    save(output / 'summary.json', summary)
    save(RESULT / 'reference_summary.json', summary)
    print('v7十六例汇总', json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'run'))
    args = parser.parse_args()
    freeze() if args.stage == 'freeze' else run()


if __name__ == '__main__':
    main()
