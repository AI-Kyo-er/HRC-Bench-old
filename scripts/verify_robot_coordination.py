#!/usr/bin/env python3
"""核对机器人视觉协调输入、原始模型选择、控制来源和双向公开消息。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hrc_pilot.robot_coordination import PUBLIC_KEYS,validate_decision,execution_feedback


def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_episode(directory):
    plans=rows(directory/'robot_planner_io.jsonl');calls=rows(directory/'model_calls.jsonl')
    human=rows(directory/'human_policy_io.jsonl');dialogue=rows(directory/'public_dialogue.jsonl')
    trace={row['step']:row for row in rows(directory/'trace.jsonl')}
    actions=rows(directory/'policy_io.jsonl')
    by_id={row['decision_id']:row for row in plans}
    for row in plans:
        expected_keys=PUBLIC_KEYS-{'images'}
        if 'self_execution' not in row['public_input']:expected_keys=expected_keys-{'self_execution'}
        assert set(row['public_input'])==expected_keys
        decision,error=validate_decision(row['raw_output'])
        assert decision==row['decision'] and error==row['parse_error']
        for name,field in [('initial','initial_artifact'),('current','exterior_artifact'),('wrist','wrist_artifact')]:
            pixels=np.asarray(Image.open(directory/row[field]).convert('RGB'))
            assert sha256(pixels.tobytes()).hexdigest()==row['image_sha256'][name]
        np.testing.assert_allclose(row['public_input']['state'][:3],trace[row['step']]['robot_ee'],atol=1e-6)
        np.testing.assert_allclose(row['public_input']['state'][-2:],trace[row['step']]['robot_qpos'][-2:],atol=1e-6)
        if 'self_execution' in row['public_input']:
            expected=execution_feedback(trace[row['step']],calls[0]['state'],
                [c for c in calls if c['step']<row['step']],[a for a in actions if a['step']<row['step']])
            actual=row['public_input']['self_execution']
            for key,value in expected.items():
                if key=='own_contact_report' and key not in actual:continue
                if key=='eef_displacement_from_start_m':np.testing.assert_allclose(actual[key],value,atol=1e-8)
                else:assert actual[key]==value
    for call in calls:
        plan=by_id[call['planner_decision_id']]
        assert plan['step']<=call['step']
        if call['action_source']=='learned_vla':
            assert plan['decision']['mode']=='execute'
            assert call['prompt']==plan['decision']['instruction']
        else:
            assert plan['decision']['mode']=='hold'
            assert (call['action_source']=='planner_output_rejection_hold_primitive')==(plan['parse_error'] is not None)
    robot_messages=[m['text'] for m in dialogue if m['speaker']=='robot' and m['kind']=='policy_message']
    assert robot_messages==[p['decision']['message'] for p in plans if p['decision']['message']]
    seen=sum(any(m['speaker']=='robot' and m['kind']=='policy_message'
                 for m in json.loads(row['public_input'].split('\n',1)[1])['public_dialogue']) for row in human)
    return {'episode':str(directory),'planner_calls':len(plans),'robot_messages':len(robot_messages),
            'human_model_inputs_containing_robot_messages':seen,
            'planner_parse_errors':sum(p['parse_error'] is not None for p in plans),
            'vla_calls':sum(c['action_source']=='learned_vla' for c in calls),
            'hold_primitive_calls':sum(c['action_source']!='learned_vla' for c in calls),
            'public_visual_input_reconstructed':True,'model_decisions_and_execution_sources_reconstructed':True,
            'interpretation':'核查原始模型决定、视觉输入、控制来源与公开消息传递；不证明理解、协商成功或cobalance效度。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[verify_episode(p.parent) for p in args.input_dir.rglob('robot_planner_io.jsonl')]
    assert episodes
    (args.input_dir/'coordination_verification.json').write_text(json.dumps({'status':'verified','episodes':episodes},ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条视觉协调与双向消息链路核查通过')


if __name__=='__main__':main()
