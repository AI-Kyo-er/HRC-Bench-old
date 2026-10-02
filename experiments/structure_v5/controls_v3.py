"""独立开发：blue先入盘再跨盘返工；不改旧冻结世界/任务。"""
import argparse
import datetime
import json
from pathlib import Path

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.world_v3 import AuditedReworkWorld as SafeParkingWorld

RESULT = ROOT / 'results/structure_v5'
SOURCES = ['experiments/physical/world.py', 'experiments/physical_v3_2/world.py',
           'experiments/structure_v5/controls_v3.py', 'experiments/structure_v5/world.py', 'experiments/structure_v5/world_v2.py', 'experiments/structure_v5/world_v3.py']


def cases():
    return [{'id': f'blue_rework_{source}_{target}_{route}_40', 'seed': 40,
             'source': source, 'target': target, 'route': route}
            for source, target in [('left', 'right'), ('right', 'left')]
            for route in ('direct', 'careful')]


def run(output):
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('独立控制目录非空，禁止覆盖。')
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for case in cases():
        folder = output / case['id']
        folder.mkdir()
        world = SafeParkingWorld(case['seed'], trace_path=folder / 'ticks.jsonl.gz')
        try:
            initial = world.state()
            staging = world.pick_place('blue', case['source'], 'direct')
            staged = world.state()
            occupied = world.move_partner(True)
            denied_direct = world.pick_place('blue', case['target'], 'direct')
            released = world.move_partner(False) if case['route'] == 'direct' else None
            before_return = world.state()
            rework = world.pick_place('blue', case['target'], case['route'])
            final = world.state()
            passed = (staging['success'] and rework['success'] and occupied['reached'] and
                (released is None or released['reached']) and not denied_direct['physical_attempt'] and
                world.at_goal('blue', case['target']) and not world.at_goal('blue', case['source']) and
                world.contact_audit['robot_partner_ticks'] == 0 and world.object_partner_audit['ticks'] == 0)
            record = {'case': case, 'initial': initial, 'staging': staging, 'staged': staged,
                'partner_occupy': occupied, 'blocked_direct_without_execution': denied_direct,
                'partner_release': released, 'before_return': before_return, 'rework': rework,
                'final': final, 'contact_audit': dict(world.contact_audit),
                'parking_waypoint_errors': world.parking_waypoint_errors, 'passed': passed,
                'robot_id': world.robot, 'partner_id': world.partner, 'object_ids': world.objects, 'object_partner_audit': world.object_partner_audit}
            save(folder / 'summary.json', record)
            records.append(record)
            print(case['id'], 'stage', staging['success'], 'rework', rework['success'],
                  'partner_contact_ticks', world.contact_audit['robot_partner_ticks'],
                  'passed', passed, flush=True)
        finally:
            world.close()
    summary = {'version': 'structure-v5-control-dev-3', 'cases': len(records),
        'passed': sum(r['passed'] for r in records), 'all_passed': all(r['passed'] for r in records),
        'physical_attempts': sum(int(r[name]['physical_attempt']) for r in records for name in ('staging', 'rework')),
        'physical_successes': sum(r[name]['success'] for r in records for name in ('staging', 'rework')),
        'robot_partner_ticks': sum(r['contact_audit']['robot_partner_ticks'] for r in records),
        'total_ticks': sum(r['contact_audit']['total_ticks'] for r in records),
        'source_sha256': {name: sha(ROOT / name) for name in SOURCES},
        'packages': versions(), 'assets_sha256': asset_hashes(),
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'interpretation': '独立低层可行性开发，只有blue跨盘/伙伴几何覆盖；不代表任务语义或模型能力验收。'}
    save(output / 'summary.json', summary)
    save(RESULT / 'control_dev_3_summary.json', summary)
    print('返工控制结果', json.dumps({k: summary[k] for k in
          ('passed', 'cases', 'physical_successes', 'robot_partner_ticks', 'total_ticks')}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=RESULT / 'raw/control_dev_3')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
