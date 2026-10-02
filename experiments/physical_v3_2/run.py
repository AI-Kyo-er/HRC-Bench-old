"""v3.2控制验收与独立多物品接口开发诊断；不重跑v3.1 formal。"""
import argparse
import hashlib
import json
from pathlib import Path

from experiments.physical.protocol import Episode, reference, parse, SYSTEM
from experiments.physical.run import ROOT, sha, save, metadata, model_backend
from .progress import dev_cases, messages, public_progress, snapshot_observation

RAW = ROOT / 'results/physical_v3_2/raw'
FREEZE = ROOT / 'experiments/physical_v3_2/cases/dev_freeze.json'
SOURCE = ['experiments/physical_v3_2/world.py', 'experiments/physical_v3_2/progress.py',
          'experiments/physical_v3_2/run.py', 'experiments/physical_v3_2/audit.py']


def local_metadata():
    return {**metadata(), 'version': 'control-and-progress-dev-v3.2',
            'new_source_sha256': {name: sha(ROOT / name) for name in SOURCE}}


def controls(output):
    from .world import SafeParkingWorld
    from experiments.physical.world import ITEMS, TARGETS
    basic = []
    for route in ('direct', 'careful'):
        for item in ITEMS:
            for destination in TARGETS:
                name = f'{route}_{item}_{destination}'
                world = SafeParkingWorld(seed=20, occupied=route == 'careful',
                    trace_path=output / f'{name}_ticks.jsonl.gz')
                try:
                    result = world.pick_place(item, destination, route)
                    row = {'id': name, 'result': result, 'contact_audit': world.contact_audit,
                           'parking_errors': world.parking_waypoint_errors}
                    basic.append(row)
                    print(name, result['success'], row['contact_audit'], row['parking_errors'], flush=True)
                finally:
                    world.close()
    episodes = []
    for seed in (20, 21):
        for accepts in (False, True):
            for condition in ('upfront', 'revision'):
                case = {'id': f'control_{condition}_{seed}_{int(accepts)}', 'condition': condition,
                        'seed': seed, 'partner_accepts': accepts, 'reverse_menu': bool(seed % 2), 'step_budget': 12}
                folder = output / case['id']
                folder.mkdir()
                world = SafeParkingWorld(seed=seed, trace_path=folder / 'ticks.jsonl.gz',
                    render_dir=folder / 'frames' if case['id'] == 'control_revision_21_0' else None)
                ep = Episode(case, world)
                rows = []
                try:
                    for _ in range(case['step_budget']):
                        if ep.success():
                            break
                        obs = snapshot_observation(ep.observation())
                        choice = reference(obs)
                        result = ep.act(choice)
                        rows.append({'observation': obs, 'choice': choice, 'result': result})
                        print(case['id'], choice, result['feedback'], flush=True)
                    record = {'case': case, 'success': ep.success(), 'cost': ep.cost,
                              'contact_audit': world.contact_audit, 'parking_errors': world.parking_waypoint_errors,
                              'partner_motion_failures': sum(not r['result']['partner_motion']['reached']
                                  for r in rows if 'partner_motion' in r['result'])}
                    episodes.append(record)
                    save(folder / 'decisions.json', rows)
                    save(folder / 'summary.json', record)
                finally:
                    world.close()
    contact_ticks = sum(r['contact_audit']['robot_partner_ticks'] for r in basic + episodes)
    peak_error = max(error for row in basic + episodes for errors in row['parking_errors'] for error in errors)
    summary = {'basic_success': sum(r['result']['success'] for r in basic), 'basic_total': len(basic),
               'continuous_success': sum(r['success'] for r in episodes), 'continuous_total': len(episodes),
               'robot_partner_contact_ticks': contact_ticks,
               'max_contact_normal_force': max(r['contact_audit']['max_normal_force'] for r in basic + episodes),
               'total_physics_ticks_audited': sum(r['contact_audit']['total_ticks'] for r in basic + episodes),
               'max_parking_waypoint_error': peak_error,
               'partner_motion_failures': sum(r['partner_motion_failures'] for r in episodes),
               'control_passed': all(r['result']['success'] for r in basic) and all(r['success'] for r in episodes)
                                 and contact_ticks == 0 and peak_error < .02
                                 and all(r['partner_motion_failures'] == 0 for r in episodes),
               'metadata': local_metadata(), 'basic': basic, 'continuous': episodes,
               'scope': '新开发控制覆盖，成功与全轨迹robot-partner无接触同时检查；不表示任意场景安全。'}
    save(output / 'summary.json', summary)
    save(ROOT / 'results/physical_v3_2/control_summary.json', summary)


def freeze_dev():
    if FREEZE.exists():
        raise RuntimeError('开发诊断已冻结，禁止覆盖。')
    cases = dev_cases()
    record = {'stage': 'post-hoc independent multi-item interface dev diagnostic',
              'cases': cases, 'views': ['full_history', 'public_progress_aid'],
              'metadata': local_metadata(), 'system': SYSTEM,
              'limitations': '新开发fixture由v3.1失败启发，不是结构留出或物理rollout。辅助明确增加公开历史外部归约，两view长度不同。'}
    save(FREEZE, record)
    print('DEV_FROZEN', sha(FREEZE), flush=True)


def dev(output):
    frozen = json.loads(FREEZE.read_text())
    if frozen['metadata']['new_source_sha256'] != local_metadata()['new_source_sha256']:
        raise RuntimeError('开发诊断源版本与冻结不一致。')
    model = model_backend()
    rows = []
    for case in frozen['cases']:
        for view in frozen['views']:
            msg = messages(case['observation'], view)
            prediction = model.predict(msg)
            choice, error = parse(prediction['response'], case['observation']['candidates'])
            row = {'case': case, 'view': view, 'messages': msg, 'prediction': prediction,
                   'choice': choice, 'parse_error': error,
                   'progress_choice': choice in case['allowed_progress_choices'],
                   'derived_public_progress': public_progress(case['observation'])}
            rows.append(row)
            print(case['id'], view, choice, row['progress_choice'], flush=True)
    summary = {'views': {view: {'progress_choices': sum(r['progress_choice'] for r in rows if r['view'] == view),
                  'total': sum(r['view'] == view for r in rows),
                  'parse_errors': sum(r['parse_error'] is not None for r in rows if r['view'] == view),
                  'by_completed_item': {item: {'progress_choices': sum(r['progress_choice'] for r in rows
                      if r['view'] == view and r['case']['completed_item'] == item), 'total': 4}
                      for item in ('red', 'blue', 'green')}} for view in frozen['views']},
               'generation_hit_limit': sum(r['prediction']['generation_hit_limit'] for r in rows),
               'model': model.metadata(), 'metadata': local_metadata(),
               'dev_freeze_sha256': sha(FREEZE),
               'interpretation': '24次单调用开发诊断，不是闭环或物理任务成功率；辅助是独立有帮助baseline，不是裸模型。'}
    save(output / 'calls.json', rows)
    save(output / 'summary.json', summary)
    save(ROOT / 'results/physical_v3_2/progress_dev_summary.json', summary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('controls', 'freeze-dev', 'dev'))
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    output = args.output_dir or RAW / args.stage
    if args.stage == 'freeze-dev':
        freeze_dev()
        return
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('输出目录非空，不覆盖既有结果。')
    if args.stage == 'controls':
        controls(output)
    else:
        dev(output)


if __name__ == '__main__':
    main()
