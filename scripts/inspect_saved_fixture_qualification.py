"""检查已保存的完整资格轨迹，不重跑或伪造缺失的原始provenance。"""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from robosuite.utils.binding_utils import MjSim

from hrc_pilot.fixture_area_human_executor import CONTRACT
from hrc_pilot.fixture_receipt_verification import verify_fixture_receipts
from hrc_pilot.video_verification import verify_episode


def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


if __name__=='__main__':
    root=Path('results/continuous_v2/fixture_surface_qualification_20261009');ep=root/'episode'
    trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl')
    controls=rows(ep/'robot_control.jsonl');calls=rows(ep/'model_calls.jsonl')
    receipts=rows(ep/'human_command_receipts.jsonl');motion=rows(ep/'human_control.jsonl')
    assert len(trace)==801 and len(controls)==800 and trace[-1]['time_s']==40
    assert all(c['action_source']=='reference_scheduler_hold' for c in calls)
    assert all(h['neural_inferences']==0 for h in human)
    assert all(m['robot_pose_writes']==0 for m in motion)
    assert max(np.linalg.norm(m['hand_velocity']) for m in motion)<=.200001
    for c,pre,post in zip(controls,trace,trace[1:]):
        call=calls[c['model_call_id']]
        np.testing.assert_allclose(c['action'],call['raw_action_chunk'][c['step']-call['step']])
        assert c['source']==call['action_source']
        np.testing.assert_allclose([c['pre_physics_time_s'],c['post_physics_time_s']],
            [pre['physics_time_s'],post['physics_time_s']],atol=1e-7)
    sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
    regions=json.loads((ep/'task.json').read_text())['regions']
    checks=verify_fixture_receipts({'human_fixture_surface_contract':CONTRACT},trace,human,receipts,sim,regions)
    video=verify_episode(ep,root,require_timeline=True)
    assert video['status']=='verified' and video['video']['decoded_frames']==801
    output={'status':'saved_trace_and_video_checks_passed','role':'diagnostic_execution_qualification_not_formal',
        'original_failure_preserved':json.loads((root/'failure.json').read_text()),
        'original_provenance_missing':not (root/'provenance.json').exists(),
        'standard_interaction_verification':'not_claimed_missing_original_provenance',
        'actual_control_steps':len(controls),'human_neural_calls':0,'robot_neural_calls':0,
        'fixture_receipts':checks,'video':video,'terminal_objects':trace[-1]['objects'],
        'human_terminal_execution':trace[-1]['human_execution'],
        'scope':'只检查原保存轨迹／模型调用来源／家具面回执／完整视频；未重跑、不补造原始设置，不认证人策略或机器人协作。',
        'source_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in [
            Path(__file__),ep/'trace.jsonl',ep/'human_policy_io.jsonl',ep/'robot_control.jsonl',
            ep/'human_command_receipts.jsonl',ep/'model_calls.jsonl',ep/'scene.xml']}}
    (root/'saved_trace_verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(json.dumps({'status':output['status'],'controls':len(controls),'fixture_receipts':len(checks),
        'video_frames':video['video']['decoded_frames'],'original_failure_preserved':True}))
