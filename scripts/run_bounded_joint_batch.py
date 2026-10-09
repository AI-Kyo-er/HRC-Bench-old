"""有限文本伙伴的三活动完整开发批；失败保留，不自动重试或挑选结果。"""
import argparse
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from hrc_pilot.bounded_human_protocol import TEXT_LIMITS
from hrc_pilot.bounded_human_runtime import PROTOCOL, HISTORY_ENCODING
from hrc_pilot.video_verification import verify_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conditions', type=Path, required=True)
    parser.add_argument('--human-model', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    table = args.conditions
    digest = sha256(table.read_bytes()).hexdigest()
    conditions = list(csv.DictReader(table.open()))
    roots = [Path('results/continuous_v2') / row['run'] for row in conditions]
    if len(conditions) != 3 or {row['activity'] for row in conditions} != {
        'drawer_access', 'drink_storage', 'snack_service'
    }:
        raise ValueError('本批必须保留预定的三个不同活动')
    if any(root.exists() for root in roots):
        raise ValueError('已有结果不能覆盖、自动重试或隐式续跑')
    for row, root in zip(conditions, roots):
        if sha256(table.read_bytes()).hexdigest() != digest:
            raise ValueError('预定条件表已变化')
        command = [sys.executable, 'scripts/run_bounded_joint_activity.py',
            '--activity', row['activity'], '--situation', row['situation'],
            '--profile', row['profile'], '--init-state-id', row['init_state_id'],
            '--seed', row['seed'], '--steps', row['steps'], '--context-step', '800',
            '--human-decision-steps', '80', '--coordinator-decision-steps', '80',
            '--workspace-method', '--activity-specific-context', '--human-auto-buffer',
            '--human-relational-targets', '--human-complete-observation',
            '--symbolic-coordinator', '--robot-skill-bank', '--interaction-contract',
            '--human-area-placement', '--human-contribution-observations',
            '--human-carried-observation', '--human-model', str(args.human_model),
            '--port', str(args.port), '--output-dir', str(root)]
        if row['initial_human_holding'] == '1':
            command.append('--initial-human-holding')
        log = Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results') / (row['run'] + '.log')
        print(json.dumps({'starting': row, 'command': command}, ensure_ascii=False), flush=True)
        with log.open('x') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=os.environ.copy())
        if result.returncode:
            raise RuntimeError('保留失败并停止本批：' + row['run'])
        (root / 'batch_condition.json').write_text(json.dumps({
            'condition': row, 'condition_table_sha256': digest,
            'human_model': str(args.human_model.resolve()), 'actual_command': command,
            'human_output_protocol': PROTOCOL, 'human_failed_history_encoding': HISTORY_ENCODING,
            'human_text_limits': TEXT_LIMITS, 'role': 'complete_joint_development_not_formal'
        }, ensure_ascii=False, indent=2))
        for script in ['audit_joint_activity.py', 'evaluate_joint_process.py']:
            subprocess.run([sys.executable, 'scripts/' + script, '--input-dir', str(root)], check=True)
        video = verify_episode(root / 'episode', root, require_timeline=True)
        (root / 'independent_video_verification.json').write_text(json.dumps(video, ensure_ascii=False, indent=2))
        if video['status'] != 'verified':
            raise RuntimeError('完整视频核查失败，结果不发布')
        subprocess.run([sys.executable, 'scripts/build_bounded_joint_report.py'], check=True)
        print(json.dumps({'condition_verified': row['run']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
