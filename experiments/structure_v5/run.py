"""先冻结开发参考语义，再运行十例公开观察规则策略；没有神经调用。"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.protocol import Episode, cases, reference, reduce_history, SYSTEM
from experiments.structure_v5.world_v3 import AuditedReworkWorld

RESULT = ROOT / 'results/structure_v5'
FREEZE = ROOT / 'experiments/structure_v5/cases/reference_freeze.json'
SOURCES = ['experiments/physical/world.py', 'experiments/physical/protocol.py',
           'experiments/physical_v3_2/world.py', 'experiments/structure_v5/world.py',
           'experiments/structure_v5/world_v2.py', 'experiments/structure_v5/world_v3.py',
           'experiments/structure_v5/protocol.py', 'experiments/structure_v5/run.py',
           'experiments/structure_v5/audit.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def freeze():
    if FREEZE.exists():
        raise RuntimeError('参考任务已冻结，禁止覆盖。')
    gates = {name: json.loads((RESULT / name).read_text()) for name in
             ('control_dev_3_summary.json', 'initial_controls_summary.json')}
    if not all(g['all_passed'] for g in gates.values()):
        raise RuntimeError('最终共享控制器未通过。')
    audit = json.loads((RESULT / 'control_contact_audit.json').read_text())
    if not all(row['audit']['zero_record_passed'] and row['audit']['all_missing_distance_records'] == 0
               for name in ('control_dev_3', 'initial_controls') for row in audit[name]):
        raise RuntimeError('最终全tick审计未通过。')
    save(FREEZE, {'version': 'structure-v5-reference-dev-1', 'cases': cases(),
        'source_sha256': source_hashes(), 'packages': versions(), 'assets_sha256': asset_hashes(),
        'control_artifact_sha256': {name: sha(RESULT / name) for name in
             ('control_dev_3_summary.json', 'initial_controls_summary.json', 'control_contact_audit.json')},
        'candidate_count': 21, 'system': SYSTEM,
        'interpretation': '十例脚本共同背景的开发规则可行性，不是模型协商、泛化/组合holdout、严格等信息因果对照；21候选新增组成需独立基础校准。'})
    print('参考语义冻结', sha(FREEZE), flush=True)


def keyframe(world, folder):
    folder.mkdir(parents=True, exist_ok=True)
    world.render_dir = folder
    world.capture()
    world.render_dir = None


def prefix_digest(path, checkpoint_tick):
    digest = hashlib.sha256()
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['tick'] > checkpoint_tick:
                break
            # 不含case、墙钟、文件路径；包含实际对象/关节/伙伴及全部接触。
            digest.update(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())
    return digest.hexdigest()


def rollout(case, folder):
    folder.mkdir(parents=True)
    world = AuditedReworkWorld(case['seed'], trace_path=folder / 'ticks.jsonl.gz')
    rows = []
    try:
        episode = Episode(case, world)
        rendered = case['id'] in ('A_exclusive_40', 'B_nested_40')
        if rendered:
            keyframe(world, folder / 'frames')
        for _ in range(case['step_budget']):
            if episode.success():
                break
            observation = episode.observation()
            messages = episode.messages()
            choice = reference(observation)
            before_tick = world.tick
            result = episode.act(choice)
            rows.append({'observation': observation, 'messages': messages,
                'prediction': {'response': json.dumps({'choice': choice}), 'policy': 'public_history_reference'},
                'result': result, 'before_tick': before_tick, 'after_tick': world.tick})
            print(case['id'], len(rows), choice, result['feedback'], flush=True)
            if rendered:
                keyframe(world, folder / 'frames')
        summary = {'case': case, 'success': episode.success(), 'cost': episode.cost,
            'checkpoint': episode.checkpoint, 'prefix_execution': episode.prefix,
            'prefix_partner_motion': episode.prefix_partner,
            'final_state': world.state(), 'final_public_reduction_for_audit': reduce_history(episode.history),
            'finish_audit': episode.finish_audit, 'contact_audit_online': copy.deepcopy(world.contact_audit),
            'object_partner_audit_online': copy.deepcopy(world.object_partner_audit),
            'body_ids': {'robot': world.robot, 'partner': world.partner, 'objects': dict(world.objects)},
            'input_lengths': [{'characters': sum(len(m['content']) for m in row['messages']),
                               'history_events': len(row['observation']['history'])} for row in rows],
            'branch_exposure': {'requests': sum(r['result']['choice'] == 'request_clear' for r in rows),
                'yields': sum(r['result']['choice'] == 'yield' for r in rows),
                'finishes': sum(r['result']['choice'] == 'finish_guidance' for r in rows),
                'green_while_guidance_active': any(r['result']['choice'].startswith(('place_green_', 'careful_green_')) and
                    reduce_history(r['observation']['history'])['active'] for r in rows)}}
        save(folder / 'decisions.json', rows)
    finally:
        world.close()
    ids = summary['body_ids']
    audit = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
    assert audit['robot_partner']['ticks'] == summary['contact_audit_online']['robot_partner_ticks']
    assert audit['object_partner']['ticks'] == summary['object_partner_audit_online']['ticks']
    assert audit['total_ticks'] == summary['contact_audit_online']['total_ticks']
    summary['contact_audit_raw_ticks'] = audit
    summary['prefix_trace_sha256'] = prefix_digest(folder / 'ticks.jsonl.gz', summary['checkpoint']['tick'])
    summary['passed'] = summary['success'] and audit['zero_record_passed']
    if case['family'] == 'B':
        finish = summary['finish_audit']
        summary['passed'] = (summary['passed'] and finish is not None and finish['before'] == finish['after'] and
            finish['green_regions_before'] == finish['green_regions_after'] and bool(finish['green_regions_before']) and
            finish['scope_active_after'] is None and not finish['global_success_immediately_after_finish'] and
            summary['branch_exposure']['green_while_guidance_active'])
    save(folder / 'summary.json', summary)
    return summary


def run():
    frozen = json.loads(FREEZE.read_text())
    if frozen['source_sha256'] != source_hashes() or frozen['packages'] != versions() or frozen['assets_sha256'] != asset_hashes():
        raise RuntimeError('代码/环境与参考冻结不一致。')
    output = RESULT / 'raw/reference'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆盖规则结果。')
    rows = [rollout(case, output / case['id']) for case in frozen['cases']]
    pairs = []
    for seed in (40, 41):
        for family in ('A', 'B'):
            subset = [r for r in rows if r['case']['seed'] == seed and r['case']['family'] == family]
            pairs.append({'seed': seed, 'family': family,
                'ids': [r['case']['id'] for r in subset],
                'checkpoint_exact_match': all(r['checkpoint'] == subset[0]['checkpoint'] for r in subset),
                'full_physical_prefix_trace_exact_match': len({r['prefix_trace_sha256'] for r in subset}) == 1,
                'checkpoint_input_lengths': [r['input_lengths'][0] for r in subset]})
    summary = {'version': frozen['version'], 'total': len(rows), 'passed': sum(r['passed'] for r in rows),
        'success': sum(r['success'] for r in rows), 'total_ticks': sum(r['contact_audit_raw_ticks']['total_ticks'] for r in rows),
        'robot_partner_ticks': sum(r['contact_audit_raw_ticks']['robot_partner']['ticks'] for r in rows),
        'object_partner_ticks': sum(r['contact_audit_raw_ticks']['object_partner']['ticks'] for r in rows),
        'pairs': pairs, 'cost': {k: sum(r['cost'][k] for r in rows) for k in rows[0]['cost']},
        'requests_exposed': sum(r['branch_exposure']['requests'] for r in rows),
        'freeze_sha256': sha(FREEZE), 'source_sha256': source_hashes(),
        'interpretation': frozen['interpretation']}
    save(output / 'summary.json', summary)
    save(RESULT / 'reference_summary.json', summary)
    print('十例参考结果', json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'run'))
    args = parser.parse_args()
    freeze() if args.stage == 'freeze' else run()


if __name__ == '__main__':
    main()
