"""最终世界对初始桌面来源的必要回归覆盖，伙伴占位下六个绕行抓放。"""
from experiments.structure_v5.world_v3 import AuditedReworkWorld
from experiments.physical.run import ROOT, save, sha


def main():
    output = ROOT / 'results/structure_v5/raw/initial_controls'
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('禁止覆盖初始来源控制。')
    rows = []
    for item in ('red', 'blue', 'green'):
        for target in ('left', 'right'):
            name = f'initial_{item}_{target}_40'
            world = AuditedReworkWorld(40, occupied=True, trace_path=output / f'{name}.jsonl.gz')
            try:
                result = world.pick_place(item, target, 'careful')
                passed = result['success'] and world.contact_audit['robot_partner_ticks'] == 0 and world.object_partner_audit['ticks'] == 0
                rows.append({'id': name, 'result': result, 'passed': passed,
                    'contact_audit': dict(world.contact_audit), 'object_partner_audit': dict(world.object_partner_audit),
                    'body_ids': {'robot': world.robot, 'partner': world.partner, 'objects': world.objects}})
                print(name, result['success'], 'robot_ticks', world.contact_audit['robot_partner_ticks'],
                      'object_ticks', world.object_partner_audit['ticks'], 'passed', passed, flush=True)
            finally:
                world.close()
    summary = {'passed': sum(r['passed'] for r in rows), 'total': len(rows),
        'all_passed': all(r['passed'] for r in rows),
        'total_ticks': sum(r['contact_audit']['total_ticks'] for r in rows),
        'source_sha256': {name: sha(ROOT / name) for name in ('experiments/structure_v5/world.py',
            'experiments/structure_v5/world_v2.py', 'experiments/structure_v5/world_v3.py',
            'experiments/structure_v5/initial_controls.py')}, 'rows': rows}
    save(output / 'summary.json', summary)
    save(ROOT / 'results/structure_v5/initial_controls_summary.json', summary)


if __name__ == '__main__':
    main()
