"""A成功率捷径的独立物理诊断，旧v5冻结及评分不变。"""
import argparse
import copy
import json

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.run import FREEZE as OLD_FREEZE, SOURCES as OLD_SOURCES
from experiments.structure_v5.protocol import Episode
from experiments.structure_v5.world_v3 import AuditedReworkWorld
from experiments.structure_v5.audit import contact_audit
from experiments.structure_diagnostic_v6.policy import BlindYieldThenDetour

RESULT = ROOT / 'results/structure_diagnostic_v6'
FREEZE = ROOT / 'experiments/structure_diagnostic_v6/cases/freeze_v1.json'
SOURCES = OLD_SOURCES + ['experiments/structure_diagnostic_v6/policy.py',
                         'experiments/structure_diagnostic_v6/run_v1.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def freeze():
    if FREEZE.exists():
        raise RuntimeError('独立捷径诊断已冻结，禁止覆盖。')
    old = json.loads(OLD_FREEZE.read_text())
    save(FREEZE, {'version': 'A-blind-yield-v6.1', 'cases': [c for c in old['cases'] if c['family'] == 'A'],
        'old_freeze_sha256': sha(OLD_FREEZE), 'source_sha256': source_hashes(),
        'packages': versions(), 'assets_sha256': asset_hashes(),
        'policy': '首次无条件yield，之后只读初始公开物品目标和实际物理区域，永远careful；不使用passage/yield反馈或当前约定归约。',
        'interpretation': '事后可辨识性诊断，不改旧约定或增惩罚；按实际成本比较，不把候选合法等同所有路径已验收。'})
    print('独立捷径冻结', sha(FREEZE), flush=True)


def rollout(case, folder):
    folder.mkdir(parents=True)
    world = AuditedReworkWorld(case['seed'], trace_path=folder / 'ticks.jsonl.gz')
    rows = []
    try:
        episode = Episode(case, world)
        policy = BlindYieldThenDetour()
        for _ in range(case['step_budget']):
            if episode.success():
                break
            observation = episode.observation()
            messages = episode.messages()
            before = copy.deepcopy(world.state())
            choice = policy.choose(observation)
            result = episode.act(choice)
            after = copy.deepcopy(world.state())
            rows.append({'observation': observation, 'messages': messages,
                'prediction': {'response': json.dumps({'choice': choice}), 'policy': 'blind_yield_then_detour'},
                'result': result, 'before_physical_state': before, 'after_physical_state': after})
            print(case['id'], len(rows), choice, result['feedback'], flush=True)
        summary = {'case': case, 'success': episode.success(), 'cost': episode.cost,
            'checkpoint': episode.checkpoint, 'final_state': world.state(),
            'initial_goals_used': policy.initial_goals,
            'first_yield_valid': rows[0]['result']['valid'],
            'first_yield_ticks': rows[0]['after_physical_state']['tick'] - rows[0]['before_physical_state']['tick'],
            'first_yield_physical_state_unchanged': rows[0]['after_physical_state'] == rows[0]['before_physical_state'],
            'work_ticks_after_checkpoint': world.tick - episode.checkpoint['tick'],
            'body_ids': {'robot': world.robot, 'partner': world.partner, 'objects': dict(world.objects)},
            'online_robot_partner': copy.deepcopy(world.contact_audit),
            'online_object_partner': copy.deepcopy(world.object_partner_audit)}
        save(folder / 'decisions.json', rows)
    finally:
        world.close()
    ids = summary['body_ids']
    summary['contact_audit_raw_ticks'] = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
    assert summary['contact_audit_raw_ticks']['robot_partner']['ticks'] == summary['online_robot_partner']['robot_partner_ticks']
    assert summary['contact_audit_raw_ticks']['object_partner']['ticks'] == summary['online_object_partner']['ticks']
    summary['passed'] = summary['success'] and summary['contact_audit_raw_ticks']['zero_record_passed']
    save(folder / 'summary.json', summary)
    return summary


def run():
    frozen = json.loads(FREEZE.read_text())
    if source_hashes() != frozen['source_sha256'] or sha(OLD_FREEZE) != frozen['old_freeze_sha256'] or versions() != frozen['packages'] or asset_hashes() != frozen['assets_sha256']:
        raise RuntimeError('代码/环境/旧冻结变化。')
    output = RESULT / 'raw/episodes_v1'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆盖诊断结果。')
    pairs = []
    for case in frozen['cases']:
        new = rollout(case, output / case['id'])
        old = json.loads((ROOT / 'results/structure_v5/raw/reference' / case['id'] / 'summary.json').read_text())
        assert json.loads(json.dumps(new['checkpoint'])) == old['checkpoint']
        pairs.append({'id': case['id'], 'variant': case['variant'], 'checkpoint_exact_match': True,
            'reference_success': old['success'], 'blind_success': new['success'], 'blind_passed': new['passed'],
            'reference_cost': old['cost'], 'blind_cost': new['cost'],
            'reference_total_ticks': old['contact_audit_raw_ticks']['total_ticks'],
            'blind_total_ticks': new['contact_audit_raw_ticks']['total_ticks'],
            'reference_work_ticks': old['final_state']['tick'] - old['checkpoint']['tick'],
            'blind_work_ticks': new['work_ticks_after_checkpoint'],
            'reference_robot_partner_ticks': old['contact_audit_raw_ticks']['robot_partner']['ticks'],
            'blind_robot_partner_ticks': new['contact_audit_raw_ticks']['robot_partner']['ticks'],
            'reference_object_partner_ticks': old['contact_audit_raw_ticks']['object_partner']['ticks'],
            'blind_object_partner_ticks': new['contact_audit_raw_ticks']['object_partner']['ticks'],
            'first_yield_valid': new['first_yield_valid'], 'first_yield_ticks': new['first_yield_ticks'],
            'first_yield_physical_state_unchanged': new['first_yield_physical_state_unchanged']})
    save(RESULT / 'paired_summary.json', {'version': frozen['version'], 'pairs': pairs,
        'blind_passed': sum(r['blind_passed'] for r in pairs), 'total': len(pairs),
        'freeze_sha256': sha(FREEZE), 'source_sha256': source_hashes(),
        'interpretation': frozen['interpretation']})
    print('统一策略通过', sum(r['blind_passed'] for r in pairs), '/', len(pairs), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'run'))
    args = parser.parse_args()
    freeze() if args.stage == 'freeze' else run()


if __name__ == '__main__':
    main()
