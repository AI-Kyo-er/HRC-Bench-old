"""新增neutral来源四例低层验收，完整前缀及其他物品保留。"""
import json

from experiments.physical.run import ROOT, save, sha, versions, asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v7.world import NeutralWorld

RESULT = ROOT / 'results/structure_v7'


def main():
    output = RESULT / 'raw/controls_dev0'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆盖neutral控制结果。')
    records = []
    for target in ('left', 'right'):
        for route in ('direct', 'careful'):
            name = f'neutral_to_{target}_{route}_60'
            folder = output / name
            folder.mkdir()
            world = NeutralWorld(60, trace_path=folder / 'ticks.jsonl.gz')
            try:
                red = world.pick_place('red', 'left', 'direct')
                stage = world.pick_place('blue', 'neutral', 'direct')
                occupied = world.move_partner(True)
                blocked = world.pick_place('blue', target, 'direct')
                released = world.move_partner(False)
                green = world.pick_place('green', 'right', 'direct')
                before = world.state()
                returned = world.pick_place('blue', target, route)
                final = world.state()
                passed = (all(r['success'] for r in (red, stage, green, returned)) and
                    occupied['reached'] and occupied['direct_blocked_after'] and released['reached'] and
                    not released['direct_blocked_after'] and not blocked['physical_attempt'] and
                    world.at_goal('red', 'left') and world.at_goal('green', 'right') and
                    world.at_goal('blue', target) and not world.at_goal('blue', 'neutral') and
                    world.contact_audit['robot_partner_ticks'] == 0 and world.object_partner_audit['ticks'] == 0)
                summary = {'id': name, 'target': target, 'route': route, 'red': red, 'stage': stage,
                    'partner_occupy': occupied, 'blocked_direct_without_execution': blocked,
                    'partner_release': released, 'green': green, 'before_return': before, 'returned': returned,
                    'final': final, 'passed': passed,
                    'body_ids': {'robot': world.robot, 'partner': world.partner, 'objects': dict(world.objects)},
                    'robot_partner_online': dict(world.contact_audit), 'object_partner_online': dict(world.object_partner_audit)}
            finally:
                world.close()
            ids = summary['body_ids']
            summary['contact_audit_raw_ticks'] = contact_audit(folder / 'ticks.jsonl.gz', ids['robot'], ids['partner'], ids['objects'].values())
            assert summary['contact_audit_raw_ticks']['robot_partner']['ticks'] == summary['robot_partner_online']['robot_partner_ticks']
            assert summary['contact_audit_raw_ticks']['object_partner']['ticks'] == summary['object_partner_online']['ticks']
            summary['passed'] = summary['passed'] and summary['contact_audit_raw_ticks']['zero_record_passed']
            save(folder / 'summary.json', summary)
            records.append(summary)
            print(name, 'stage', stage['success'], 'return', returned['success'],
                  'robot_ticks', summary['contact_audit_raw_ticks']['robot_partner']['ticks'],
                  'object_ticks', summary['contact_audit_raw_ticks']['object_partner']['ticks'],
                  'passed', summary['passed'], flush=True)
    summary = {'cases': len(records), 'passed': sum(r['passed'] for r in records),
        'all_passed': all(r['passed'] for r in records),
        'physical_attempts': sum(r[k]['physical_attempt'] for r in records for k in ('red', 'stage', 'green', 'returned')),
        'physical_successes': sum(r[k]['success'] for r in records for k in ('red', 'stage', 'green', 'returned')),
        'total_ticks': sum(r['contact_audit_raw_ticks']['total_ticks'] for r in records),
        'robot_partner_ticks': sum(r['contact_audit_raw_ticks']['robot_partner']['ticks'] for r in records),
        'object_partner_ticks': sum(r['contact_audit_raw_ticks']['object_partner']['ticks'] for r in records),
        'source_sha256': {name:sha(ROOT/name) for name in ('experiments/structure_v7/world.py', 'experiments/structure_v7/controls.py')},
        'packages': versions(), 'assets_sha256': asset_hashes(),
        'interpretation': '新增neutral来源的开发低层验收；不声称伙伴占位期间neutral抓取已通过。'}
    save(RESULT / 'control_summary.json', summary)
    print('neutral控制汇总', json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
