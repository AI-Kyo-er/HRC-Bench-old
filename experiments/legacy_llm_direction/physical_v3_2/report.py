"""新控制轨迹独立复核、规范日志检查及开发调用摘要，不改原始文件。"""
import gzip
import json
from pathlib import Path

from experiments.physical.analyze import audit_episode, visuals
from experiments.physical.run import ROOT, sha, save


def main():
    base = ROOT / 'results/physical_v3_2'
    folder = base / 'raw/controls_immutable'
    summary = json.loads((base / 'control_summary.json').read_text())
    independent = {}
    logs_correct = True
    for row in summary['continuous']:
        path = folder / row['case']['id']
        independent[path.name] = audit_episode(path)
        calls = json.loads((path / 'decisions.json').read_text())
        previous_history = None
        for index, call in enumerate(calls):
            history = call['observation']['history']
            if previous_history and history[:len(previous_history)] != previous_history:
                logs_correct = False
            # 当前动作的即时反馈只能出现在下一步观察，不能提前污染本步history。
            own_event = f'机器人选择{call["choice"]}。反馈：{call["result"]["feedback"]}'
            if own_event in history:
                logs_correct = False
            previous_history = history
        if (path / 'frames').exists():
            visuals(path, path)
    independent_basic = {}
    for path in sorted(folder.glob('*_ticks.jsonl.gz')):
        ticks, contact_ticks, max_force = 0, 0, 0
        for line in gzip.open(path, 'rt'):
            state = json.loads(line)
            ticks += 1
            contacts = [c for c in state['contacts'] if {c['body_a'], c['body_b']} == {1, 11}]
            if contacts:
                contact_ticks += 1
                max_force = max(max_force, max(c['normal_force'] for c in contacts))
        independent_basic[path.name] = {'ticks': ticks, 'robot_partner_ticks': contact_ticks,
                                       'max_force': max_force, 'sha256': sha(path)}
    total = sum(r['ticks'] for r in independent.values()) + sum(r['ticks'] for r in independent_basic.values())
    contact_total = sum(r['contacts']['robot_partner_ticks'] for r in independent.values()) + sum(
                            r['robot_partner_ticks'] for r in independent_basic.values())
    save(base / 'trajectory_audit.json', {'continuous': independent, 'basic': independent_basic,
        'total_physics_ticks': total, 'robot_partner_contact_ticks': contact_total,
        'log_history_immutable_checks_passed': logs_correct,
        'runtime_counter_matches': total == summary['total_physics_ticks_audited'] and
                                   contact_total == summary['robot_partner_contact_ticks']})
    if not logs_correct or contact_total != 0 or total != summary['total_physics_ticks_audited']:
        raise RuntimeError('不可变日志或独立接触审计未通过。')
    # 独立于旧存储observation字段，核对每条真实messages里的物理状态在tick轨迹出现。
    input_physics_checks = []
    old_root = ROOT / 'results/physical_v3/raw/formal_model'
    for path in sorted(old_root.glob('*/decisions.json')):
        recorded = set()
        for line in gzip.open(path.parent / 'ticks.jsonl.gz', 'rt'):
            state = json.loads(line)
            recorded.add(json.dumps([state['objects'], state['partner_position']], sort_keys=True))
        calls = json.loads(path.read_text())
        for index, call in enumerate(calls):
            physical = json.loads(call['messages'][1]['content'])['physical']
            signature = json.dumps([physical['objects'], physical['partner_position']], sort_keys=True)
            input_physics_checks.append({'case': path.parent.name, 'step': index + 1,
                                         'exact_recorded_physics_match': signature in recorded})
    save(base / 'canonical_input_physics_audit.json', {
        'calls': len(input_physics_checks), 'all_matched': all(r['exact_recorded_physics_match'] for r in input_physics_checks),
        'checks': input_physics_checks})
    if not all(r['exact_recorded_physics_match'] for r in input_physics_checks):
        raise RuntimeError('真实模型输入物理状态与逐tick轨迹不匹配。')
    dev_rows = json.loads((base / 'raw/dev/calls.json').read_text())
    paired = []
    for first, second in zip(dev_rows[::2], dev_rows[1::2]):
        paired.append({'id': first['case']['id'], 'full_history_choice': first['choice'],
            'full_history_progress': first['progress_choice'],
            'progress_aid_choice': second['choice'], 'progress_aid_progress': second['progress_choice'],
            'input_tokens': {first['view']: first['prediction']['input_tokens'],
                             second['view']: second['prediction']['input_tokens']}})
    save(base / 'dev_pair_analysis.json', paired)
    save(base / 'representative_calls.json', dev_rows[:6])
    save(base / 'execution_receipt.json', {
        'v3_1_freeze_sha256_unchanged': sha(ROOT / 'experiments/physical/cases/freeze.json'),
        'dev_freeze_sha256': sha(ROOT / 'experiments/physical_v3_2/cases/dev_freeze.json'),
        'canonical_old_message_audit_sha256': sha(base / 'message_audit.json'),
        'canonical_input_physics_audit_sha256': sha(base / 'canonical_input_physics_audit.json'),
        'control_summary_sha256': sha(base / 'control_summary.json'),
        'trajectory_audit_sha256': sha(base / 'trajectory_audit.json'),
        'progress_dev_summary_sha256': sha(base / 'progress_dev_summary.json'),
        'calls_sha256': sha(base / 'raw/dev/calls.json'),
        'analysis_source_sha256': sha(Path(__file__)),
        'sessions': {'parking_probe': 68767, 'initial_control_with_old_logging': 53401,
                     'controls_immutable': 63158, 'progress_dev': 63476},
        'scope': '开发控制与单调用诊断；未增加3B正式连续实验。'}
    )
    print('AUDIT_OK', total, contact_total, logs_correct)


if __name__ == '__main__':
    main()
