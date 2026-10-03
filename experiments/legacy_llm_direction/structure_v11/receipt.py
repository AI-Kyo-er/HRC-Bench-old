"""全部运行/审计完成后的回执，不启动新的控制或模型。"""
import datetime
import json
import subprocess

from experiments.physical.run import ROOT,save,sha
from experiments.structure_v11.run import RESULT,FREEZE,source_hashes


def main():
    reference=json.loads((RESULT/'reference_summary.json').read_text());audit=json.loads((RESULT/'input_and_pair_audit.json').read_text())
    assert reference['passed']==16 and audit['all_passed']
    check=subprocess.run(['pgrep','-af',r'^.venv-llm/bin/python -m experiments.structure_v11.(run|audit)'],capture_output=True,text=True)
    assert check.returncode==1 and not check.stdout.strip()
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==source_hashes()
    folders=[RESULT/'raw/reference'/c['id'] for c in frozen['cases']]
    source_assets=frozen['assets_sha256']
    small=['reference_summary.json','prefreeze_design_audit.json','input_and_pair_audit.json','public_strategy_diagnostic.json']
    raw=['focused_tests_attempt001.log','focused_tests.log','tests.log','freeze.log','reference.log','audit.log']
    save(RESULT/'execution_receipt.json',dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        freeze_sha256=sha(FREEZE),runtime_source_sha256=source_hashes(),runtime_source_still_matches_freeze=True,
        postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_v11/audit.py'),
        postfreeze_strategy_source_sha256=sha(ROOT/'experiments/structure_v11/strategies.py'),
        permanent_tests_sha256=sha(ROOT/'tests/test_structure_v11.py'),packages=frozen['packages'],assets_sha256=source_assets,
        old_geometric_control_reused=frozen['reused_v7_control'],new_controls_run=0,
        reference=dict(total=16,passed=16,total_ticks=reference['total_ticks'],robot_partner_ticks=reference['robot_partner_ticks'],
            object_partner_ticks=reference['object_partner_ticks'],decisions=reference['cost']['decisions'],
            physical_attempts_with_red_prefix=reference['cost']['physical_attempts']+16,
            first_blue_attempt_correct_without_prior_target_feedback=reference['first_blue_attempt_correct_without_prior_target_feedback'],
            first_blue_placement_success_without_prior_target_feedback=reference['first_blue_placement_success_without_prior_target_feedback'],
            scripted_update_events=reference['exogenous_update_events'],cost=reference['cost']),
        independent_audit=dict(all_passed=True,total_episodes=audit['total_episodes'],total_decisions=audit['total_decisions'],
            timing_pairs_passed=sum(p['passed'] for p in audit['timing_pairs']),response_pairs_passed=sum(p['disjoint'] and p['same_finish_physical'] for p in audit['response_pairs'])),
        tests=dict(first_focused_exit=1,first_focused_failure='FactsWorld初始green为None，测试误期待initial字符串；仅修测试断言，业务协议不因该失败修改。',
            final_focused_passed=6,once_full_suite_passed=52,new_tests_are_factsworld_protocol_only=True),
        observed_handles=[dict(handle=44504,stage='once_full_suite',exit_code=0),dict(handle=83101,stage='freeze',exit_code=0),
            dict(handle=97583,stage='16_actual_reference',exit_code=0),dict(handle=23788,stage='independent_audit',exit_code=0)],
        current_process_check=dict(pattern=check.args[-1],returncode=check.returncode,matches=check.stdout,active_handles=[]),
        model_calls=0,gpu_programs_started=0,downloads_started=0,
        raw_data_path=str((RESULT/'raw').resolve()),raw_data_total_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file()),
        representative_frames=[str((RESULT/'raw/reference'/f'B_update_{timing}_accepted_left_60/frames/00004.png').relative_to(ROOT)) for timing in ('before_child','during_child')],
        artifact_sha256={n:sha(RESULT/n) for n in small},raw_log_sha256={n:sha(RESULT/'raw'/n) for n in raw},
        episode_artifact_sha256={folder.name:{n:sha(folder/n) for n in ('summary.json','decisions.json','ticks.jsonl.gz')} for folder in folders},
        limits=['脚本共同背景与接受拒绝，不是模型协商','事件移动亦改变新近程度，早期决策历史不等长',
            '单层指导及一个正式更新；多更新/提前finish只FactsWorld回归','公开错误策略只离线首次choice，不是物理失败或整段失败',
            '正常菜单固定；两seed不是结构留出；无神经调用/泛化结论']))
    print('v11回执完成，无活run/audit句柄。',flush=True)


if __name__=='__main__':main()
