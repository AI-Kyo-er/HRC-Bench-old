"""原始v3.1消息/观察只读审计，独立检查历史前缀与实际区域。"""
import hashlib
import json
from pathlib import Path

from experiments.physical.run import ROOT, save, sha
from .progress import public_progress, detect_regions


def run():
    frozen = json.loads((ROOT / 'experiments/physical/cases/freeze.json').read_text())
    findings = []
    violations = []
    telemetry_warnings = []
    for path in sorted((ROOT / 'results/physical_v3/raw/formal_model').glob('*/decisions.json')):
        rows = json.loads(path.read_text())
        previous = None
        selected_remaining = 0
        repeat_detected = 0
        for index, row in enumerate(rows):
            messages = row['messages']
            obs = json.loads(messages[1]['content'])
            if obs != row['observation']:
                mismatches = [key for key in obs if obs[key] != row['observation'].get(key)]
                telemetry_warnings.append({'case': path.parent.name, 'step': index + 1,
                                           'stored_observation_differences': mismatches})
            checks = {'system_frozen': hashlib.sha256(messages[0]['content'].encode()).hexdigest()
                                       == frozen['metadata']['system_sha256'],
                      'regions_consistent_with_raw_geometry': detect_regions(obs['physical']['objects']) == obs['physical_placements'],
                      'no_scoring_complete_flag': 'completed' not in obs,
                      'all_20_candidates': len(obs['candidates']) == 20}
            if previous:
                prev = json.loads(previous['messages'][1]['content'])['history']
                checks['history_prefix_preserved'] = obs['history'][:len(prev)] == prev
                feedback = previous['result']['feedback']
                checks['prior_feedback_in_history'] = any(feedback in event for event in obs['history'][len(prev):])
            for name, passed in checks.items():
                if not passed:
                    violations.append({'case': path.parent.name, 'step': index + 1, 'check': name})
            progress = public_progress(obs)
            choice = row['result']['choice']
            item = choice.split('_')[1] if choice and choice.split('_')[0] in ('place', 'careful', 'assisted') else None
            selected_remaining += int(item in progress['remaining_items'])
            repeat_detected += int(item in progress['done_under_public_goals'])
            previous = row
        findings.append({'case': path.parent.name, 'calls': len(rows),
                         'choices_of_already_done_item_from_public_data': repeat_detected,
                         'choices_of_remaining_item': selected_remaining,
                         'decisions_sha256': sha(path)})
    result = {'input_violations': violations, 'input_checks_passed': not violations,
              'telemetry_warnings': telemetry_warnings,
              'stored_observation_history_alias_defect': bool(telemetry_warnings) and
                    all(x['stored_observation_differences'] == ['history'] for x in telemetry_warnings),
              'cases': findings, 'audited_calls': sum(f['calls'] for f in findings),
              'source_sha256': sha(Path(__file__)),
              'interpretation': '以实际predict的原始messages为规范输入，检查历史、反馈与物理区域。发现存储observation.history列表共享导致保存时变为最终历史；原始逐步messages未受影响。新版本deepcopy修复记录，旧文件保留。未发现传给模型的状态错漏；内部失败原因仍不明。'}
    save(ROOT / 'results/physical_v3_2/message_audit.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
