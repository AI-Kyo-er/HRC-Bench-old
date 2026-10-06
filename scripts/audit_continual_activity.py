#!/usr/bin/env python3
"""独立重建动态人目标与机器人目标的持续维持时间。"""
import argparse
import json
from pathlib import Path

from hrc_pilot.continual_activity_metrics import evaluate_continual_activity


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[]
    for p in sorted(args.input_dir.rglob('personal_context.json')):
        context=json.loads(p.read_text());ep=p.parent
        result=evaluate_continual_activity(rows(ep/'trace.jsonl'),rows(ep/'human_policy_io.jsonl'),context['regions'],rows(ep/'placement_evidence.jsonl'))
        episodes.append({'episode':str(ep),**result})
    assert episodes
    (args.input_dir/'continual_activity_verification.json').write_text(json.dumps({'status':'audited','episodes':episodes},ensure_ascii=False,indent=2))
    print(json.dumps([{'episode':e['episode'],'joint_released_goal_time_s':e['joint_released_goal_time_s'],'evaluable_time_s':e['human_goal_evaluable_time_s'],'target_changes':e['semantic_target_set_changes']} for e in episodes],ensure_ascii=False))


if __name__=='__main__':main()
