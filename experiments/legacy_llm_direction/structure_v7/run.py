"""控制通过后冻结8例；规则只读公开原始history，无神经调用。"""
import argparse
import copy
import json
from pathlib import Path

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import keyframe, prefix_digest
from experiments.structure_v7.world import NeutralWorld
from experiments.structure_v7.protocol import Episode, cases, reference, reduce_history, effective_blue_returns, SYSTEM

RESULT = ROOT / 'results/structure_v7'
FREEZE = ROOT / 'experiments/structure_v7/cases/reference_freeze.json'
SOURCES = ['experiments/physical/world.py', 'experiments/physical/protocol.py',
    'experiments/physical/run.py', 'experiments/physical_v3_2/world.py',
    'experiments/structure_v5/world.py', 'experiments/structure_v5/world_v2.py',
    'experiments/structure_v5/world_v3.py', 'experiments/structure_v5/audit.py',
    'experiments/structure_v5/run.py', 'experiments/structure_v7/world.py',
    'experiments/structure_v7/controls.py', 'experiments/structure_v7/protocol.py',
    'experiments/structure_v7/run.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def freeze():
    if FREEZE.exists():
        raise RuntimeError('禁止覆盖冻结。')
    control = json.loads((RESULT / 'control_summary.json').read_text())
    if not control['all_passed'] or control['source_sha256'] != {n: sha(ROOT / n) for n in control['source_sha256']}:
        raise RuntimeError('neutral来源控制未通过或源码改变。')
    for folder in (RESULT / 'raw/controls_dev0').iterdir():
        row = json.loads((folder / 'summary.json').read_text())
        if not row['contact_audit_raw_ticks']['zero_record_passed'] or row['contact_audit_raw_ticks']['all_missing_distance_records']:
            raise RuntimeError('全tick控制证据不满足。')
    save(FREEZE, dict(version='structure-v7-neutral-reference-dev0', cases=cases(),
        source_sha256=source_hashes(), packages=versions(), assets_sha256=asset_hashes(),
        control_summary_sha256=sha(RESULT / 'control_summary.json'), system=SYSTEM, candidate_count=22,
        scoring='finish后首次blue放置尝试：包括错误目标拒绝；先前blue目标纠错次数、非blue动作/目标反馈独立记录。整段完成可利用纠错，不等同无帮助首次选择。',
        interpretation='8例脚本共同背景开发规则可行性/首次选择可辨识性；无模型协商或组合/神经泛化。'))
    print('v7冻结', sha(FREEZE), flush=True)


def rollout(case, folder):
    folder.mkdir(parents=True)
    world = NeutralWorld(case['seed'], trace_path=folder / 'ticks.jsonl.gz')
    rows = []
    try:
        episode = Episode(case, world)
        rendered = case['seed'] == 60 and not case['reverse_menu']
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
            final_state=world.state(), finish_audit=finish, finish_observation=finish_observation,
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
    finally:
        world.close()
    ids = summary['body_ids']
    audit = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
    assert audit['robot_partner']['ticks'] == summary['robot_partner_online']['robot_partner_ticks']
    assert audit['object_partner']['ticks'] == summary['object_partner_online']['ticks']
    assert audit['total_ticks'] == summary['robot_partner_online']['total_ticks']
    summary['contact_audit_raw_ticks'] = audit
    summary['prefix_to_finish_trace_sha256'] = prefix_digest(folder / 'ticks.jsonl.gz', finish['after']['tick']) if finish else None
    summary['passed'] = summary['passed'] and audit['zero_record_passed'] and audit['all_missing_distance_records'] == 0
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
    pairs = []
    for seed in (60, 61):
        for reverse in (False, True):
            pair = [r for r in rows if r['case']['seed'] == seed and r['case']['reverse_menu'] == reverse]
            without_history = [{k: v for k, v in r['finish_observation'].items() if k != 'history'} for r in pair]
            valid_sets = [set(r['effective_blue_return_actions']) for r in pair]
            check = dict(seed=seed, reverse_menu=reverse, ids=[r['case']['id'] for r in pair],
                finish_physical_checkpoint_exact_match=pair[0]['finish_audit']['after'] == pair[1]['finish_audit']['after'],
                full_physical_prefix_to_finish_exact_match=pair[0]['prefix_to_finish_trace_sha256'] == pair[1]['prefix_to_finish_trace_sha256'],
                model_visible_input_without_history_exact_match=without_history[0] == without_history[1],
                effective_blue_return_sets=[sorted(s) for s in valid_sets], effective_blue_return_sets_disjoint=not(valid_sets[0] & valid_sets[1]),
                both_global_success_at_finish_false=all(not r['finish_audit']['global_success_immediately_after_finish'] for r in pair),
                history_required_scope='首次未获blue目标纠错反馈的blue放置选择；不证明利用反馈的整个episode必败。')
            check['passed'] = all(check[k] for k in ('finish_physical_checkpoint_exact_match', 'full_physical_prefix_to_finish_exact_match',
                'model_visible_input_without_history_exact_match', 'effective_blue_return_sets_disjoint', 'both_global_success_at_finish_false'))
            pairs.append(check)
    summary = dict(version=frozen['version'], total=len(rows), passed=sum(r['passed'] for r in rows),
        success=sum(r['success'] for r in rows), first_blue_attempt_correct_without_prior_target_feedback=sum(r['first_blue_attempt_correct_without_prior_target_feedback'] for r in rows),
        first_blue_placement_success_without_prior_target_feedback=sum(r['first_blue_placement_success_without_prior_target_feedback'] for r in rows),
        total_ticks=sum(r['contact_audit_raw_ticks']['total_ticks'] for r in rows),
        robot_partner_ticks=sum(r['contact_audit_raw_ticks']['robot_partner']['ticks'] for r in rows),
        object_partner_ticks=sum(r['contact_audit_raw_ticks']['object_partner']['ticks'] for r in rows),
        pairs=pairs, cost={k: sum(r['cost'][k] for r in rows) for k in rows[0]['cost']},
        position_only_readonly_diagnostic=dict(fixed_left_first_attempt_correct=4, fixed_right_first_attempt_correct=4, total=8,
            old_opposite_region_rule_defined=0, explanation='实际finish时blue均在neutral，左右反盘规则无定义；常选left/right分别匹配四个真实有效集合，仅首次尝试诊断，无盲策略物理重跑。'),
        freeze_sha256=sha(FREEZE), source_sha256=source_hashes(), interpretation=frozen['interpretation'])
    assert len(rows) == 8
    # 常量计数也与真实目标集合逐例核对，而非仅按case标签。
    assert sum('place_blue_left' in r['effective_blue_return_actions'] for r in rows) == 4
    assert sum('place_blue_right' in r['effective_blue_return_actions'] for r in rows) == 4
    assert all(r['finish_observation']['physical_placements']['blue'] == ['neutral'] for r in rows)
    save(output / 'summary.json', summary)
    save(RESULT / 'reference_summary.json', summary)
    print('v7八例汇总', json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'run'))
    args = parser.parse_args()
    freeze() if args.stage == 'freeze' else run()


if __name__ == '__main__':
    main()
