"""新v3开发校准、控制验证和冻结物理pilot的独立入口。"""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import time

from .protocol import (Episode, SYSTEM, PROMPT_VERSION, calibration_cases,
                       calibration_messages, candidates, formal_cases, parse, reference)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'results/physical_v3/raw'
FREEZE = ROOT / 'experiments/physical/cases/freeze.json'
SOURCES = ['experiments/physical/world.py', 'experiments/physical/protocol.py',
           'experiments/physical/run.py', 'experiments/language/backend.py']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def versions():
    return {p: importlib.metadata.version(p) for p in
            ('pybullet', 'numpy', 'pillow', 'mani_skill', 'sapien', 'torch', 'transformers')}


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def asset_hashes():
    import pybullet_data
    root = Path(pybullet_data.getDataPath())
    names = sorted((root / 'franka_panda').rglob('*'))
    names += [root / 'plane.urdf', root / 'plane100.obj', root / 'checker_blue.png']
    return {str(path.relative_to(root)): sha(path) for path in names if path.is_file()}


def metadata():
    return {'source_sha256': source_hashes(), 'packages': versions(),
            'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'assets_sha256': asset_hashes(), 'physics': {'backend': 'pybullet DIRECT CPU',
             'dt': 1 / 240, 'numSolverIterations': 100, 'render': 'ER_TINY_RENDERER CPU',
             'runtime_object_teleport': False, 'attachment': False},
            'prompt_version': PROMPT_VERSION, 'system_sha256': hashlib.sha256(SYSTEM.encode()).hexdigest(),
            'model_revision': 'aa8e72537993ba99e69dfaafa59ed015b17504d1',
            'model_path': str((ROOT / 'models/Qwen2.5-3B-Instruct').resolve())}


def model_backend():
    from experiments.language.backend import LocalModel
    return LocalModel(ROOT / 'models/Qwen2.5-3B-Instruct', max_new_tokens=96)


def calibrate(output):
    model = model_backend()
    records = []
    for case in calibration_cases():
        messages = calibration_messages(case)
        prediction = model.predict(messages)
        choice, error = parse(prediction['response'], case['menu'])
        row = {**case, 'messages': messages, 'prediction': prediction, 'choice': choice,
               'parse_error': error, 'acceptable': choice in case['allowed']}
        records.append(row)
        print(case['id'], choice, row['acceptable'], flush=True)
    by_mode = {m: {'acceptable': sum(r['acceptable'] for r in records if r['mode'] == m),
                   'total': sum(r['mode'] == m for r in records)}
               for m in ('solo', 'assisted', 'yield', 'refusal')}
    summary = {'n': len(records), 'acceptable': sum(r['acceptable'] for r in records),
               'by_mode': by_mode, 'parse_errors': sum(r['parse_error'] is not None for r in records),
               'generation_hit_limit': sum(r['prediction']['generation_hit_limit'] for r in records),
               'calibration_passed': all(r['acceptable'] for r in records),
               'interpretation': '独立开发单调用动作接口校准；不是物理成功率或结构泛化测试。',
               'model': model.metadata(), 'metadata': metadata()}
    save(output / 'calls.json', records)
    save(output / 'summary.json', summary)
    save(ROOT / 'results/physical_v3/calibration_summary.json', summary)


def rollout(case, policy, output, model=None, render=False):
    from .world import World
    output.mkdir(parents=True, exist_ok=True)
    world = World(case['seed'], trace_path=output / 'ticks.jsonl.gz',
                  render_dir=output / 'frames' if render else None)
    ep = Episode(case, world)
    rows = []
    try:
        for _ in range(case['step_budget']):
            if ep.success():
                break
            observation = ep.observation()
            messages = ep.messages()
            if policy == 'model':
                prediction = model.predict(messages)
                choice, error = parse(prediction['response'], observation['candidates'])
            else:
                choice, error = reference(observation), None
                prediction = {'response': json.dumps({'choice': choice}), 'policy': 'public_reference'}
            result = ep.act(choice)
            rows.append({'observation': observation, 'messages': messages,
                         'prediction': prediction, 'parse_error': error, 'result': result})
            print(case['id'], policy, ep.cost['decisions'], choice, result['feedback'], flush=True)
        summary = {'case': case, 'policy': policy, 'success': ep.success(),
                   'completed': ep.completed(), 'cost': ep.cost,
                   'final_state': world.state(), 'calls': len(rows),
                   'parse_errors': sum(r['parse_error'] is not None for r in rows),
                   'partner_motion_failures': sum(not r['result']['partner_motion']['reached']
                                                   for r in rows if 'partner_motion' in r['result']),
                   'generation_hit_limit': sum(r['prediction'].get('generation_hit_limit', False) for r in rows)}
        save(output / 'decisions.json', rows)
        save(output / 'summary.json', summary)
        return summary
    finally:
        world.close()


def controls(output):
    from .world import World, ITEMS, TARGETS
    output.mkdir(parents=True, exist_ok=True)
    basic = []
    for route in ('direct', 'careful'):
        for item in ITEMS:
            for target in TARGETS:
                name = f'basic_{route}_{item}_{target}'
                world = World(seed=0, occupied=route == 'careful', trace_path=output / f'{name}.jsonl.gz')
                try:
                    blocked = world.pick_place(item, target, 'direct') if route == 'careful' else None
                    result = world.pick_place(item, target, route)
                    basic.append({'id': name, 'result': result, 'blocked_direct_control': blocked})
                    print(name, result['success'], 'lift', result.get('lifted_z'), flush=True)
                finally:
                    world.close()
    continuous = []
    for case in formal_cases():
        dev = {**case, 'seed': case['seed'] - 10,
               'id': case['id'].replace('formal', 'dev')}
        continuous.append(rollout(dev, 'reference', output / dev['id'],
                                  render=dev['id'] == 'dev_revision_10_0'))
    summary = {'basic_success': sum(r['result']['success'] for r in basic), 'basic_total': len(basic),
               'continuous_success': sum(r['success'] for r in continuous), 'continuous_total': len(continuous),
               'blocked_direct_without_execution': sum(
                    bool(r['blocked_direct_control'] and not r['blocked_direct_control']['physical_attempt'])
                    for r in basic),
               'partner_motion_failures': sum(r['partner_motion_failures'] for r in continuous),
               'control_passed': all(r['result']['success'] for r in basic) and
                                 all(r['success'] and r['partner_motion_failures'] == 0 for r in continuous),
               'metadata': metadata()}
    save(output / 'basic.json', basic)
    save(output / 'continuous.json', continuous)
    save(output / 'summary.json', summary)
    save(ROOT / 'results/physical_v3/control_summary.json', summary)


def freeze():
    if FREEZE.exists():
        raise RuntimeError('冻结文件已存在，禁止覆盖；新协议需新版本。')
    controls_path = ROOT / 'results/physical_v3/control_summary.json'
    calibration_path = ROOT / 'results/physical_v3/calibration_summary.json'
    control = json.loads(controls_path.read_text())
    calibration = json.loads(calibration_path.read_text())
    if not control['control_passed']:
        raise RuntimeError('共享控制器或伙伴到位开发验证未通过，禁止物理pilot。')
    record = {'version': 'physical-v3.1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'cases': formal_cases(), 'metadata': metadata(),
              'calibration_summary_sha256': sha(calibration_path),
              'control_summary_sha256': sha(controls_path),
              'calibration_passed': calibration['calibration_passed'],
              'model_pilot_status': '探索性物理诊断；开发接口仍有基础目标选择错误，不做交互结构归因。',
              'protocol': {'upfront': '起点公开最终目标；第一次物理成功后仅确认原目标。',
                           'revision': '起点blue目标与最终目标相反；第一次物理成功后接受blue局部修正，其他目标保持。',
                           'partner': '第一次物理成功后电机占位。只有request_clear后才出现接受/拒绝回应；接受则实际撤离，拒绝保留占位。两件完成后再次占位并明确要求yield撤离。',
                           'termination': '当前已接受的最终目标全部由物体位置/速度满足，或12次高层决策耗尽。',
                           'candidate_order': 'seed10正常顺序，seed11反序；该轴在pilot中与目标反转、seed耦合，不能独立估计顺序效应。'},
              'notes': '小规模物理pilot；目标/伙伴回应交叉，upfront与revision最终目标及物理事件相同；非v2公平同比。'}
    save(FREEZE, record)
    print(FREEZE, sha(FREEZE), flush=True)


def formal(policy, output, render):
    frozen = json.loads(FREEZE.read_text())
    if frozen['metadata']['source_sha256'] != source_hashes():
        raise RuntimeError('执行代码与正式冻结不一致。')
    if frozen['metadata']['packages'] != versions() or frozen['metadata']['assets_sha256'] != asset_hashes():
        raise RuntimeError('依赖/物理资产与正式冻结不一致。')
    model = model_backend() if policy == 'model' else None
    records = []
    for index, case in enumerate(frozen['cases']):
        records.append(rollout(case, policy, output / case['id'], model, render=render and index == 1))
    summary = {'policy': policy, 'success': sum(r['success'] for r in records), 'total': len(records),
               'completed_items': sum(len(r['completed']) for r in records),
               'by_condition': {condition: {'success': sum(r['success'] for r in records if r['case']['condition'] == condition),
                    'total': sum(r['case']['condition'] == condition for r in records)} for condition in ('upfront', 'revision')},
               'cost': {key: sum(r['cost'][key] for r in records) for key in records[0]['cost']},
               'parse_errors': sum(r['parse_errors'] for r in records),
               'generation_hit_limit': sum(r['generation_hit_limit'] for r in records),
               'partner_motion_failures': sum(r['partner_motion_failures'] for r in records),
               'freeze_sha256': sha(FREEZE), 'metadata': metadata(),
               'model': model.metadata() if model else None,
               'visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
               'records': records}
    save(output / 'summary.json', summary)
    save(ROOT / f'results/physical_v3/formal_{policy}_summary.json', summary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('calibrate', 'controls', 'freeze', 'formal'))
    parser.add_argument('--policy', choices=('reference', 'model'), default='reference')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    output = args.output_dir or RAW / (args.stage + ('_' + args.policy if args.stage == 'formal' else ''))
    if args.stage == 'freeze':
        freeze()
    else:
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise RuntimeError('输出目录非空，不覆盖既有尝试；指定新的独立目录。')
        if args.stage == 'calibrate':
            calibrate(output)
        elif args.stage == 'controls':
            controls(output)
        else:
            formal(args.policy, output, args.render)


if __name__ == '__main__':
    main()
