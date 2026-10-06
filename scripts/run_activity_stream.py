#!/usr/bin/env python3
"""保持真实世界与双方历史的三活动模型运行，保存一条连续Sim视频。"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from openpi_client.websocket_client_policy import WebsocketClientPolicy
from hrc_pilot.activity_stream import run_activity_stream
from hrc_pilot.backend_options import add_backend_options, configure_backend, backend_provenance
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.goal_regions import visible_goal_scenario
from hrc_pilot.llm_human import QwenHumanPolicy
from hrc_pilot.openpi_adapter import DroidVLAAdapter
from hrc_pilot.video_verification import finalize_video_verification
from scripts.run_openpi_benchmark import public_robot_instruction


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend='genesis',experiment_tier='important',robot_grasp_model='friction_contact',render_stride=4)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=23)
    parser.add_argument('--ticks-per-activity',type=int,default=450)
    parser.add_argument('--human-persona',choices=['cooperative','independent','cautious','assertive'],default='cooperative')
    parser.add_argument('--human-model',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B'))
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('请使用新输出目录')
    args.policy='pi05_contact_position_activity_stream'
    args.partner_mode='qwen_llm'
    factory=configure_backend(args,parser,args.output_dir)
    base=CONTINUOUS_SCENARIOS['relay']
    first=replace(base,tick_hz=15,max_steps=args.ticks_per_activity)
    second=replace(base,name='activity_reprioritization',description='把刚整理的红蓝物体移到留用区，机器人整理剩余绿色物体。',
                   human_targets={'red':'keep_red','blue':'keep_blue'},robot_targets={'green':'tray_green'},
                   tick_hz=15,max_steps=args.ticks_per_activity,activity=None)
    third=replace(base,name='activity_role_exchange',description='重新整理：机器人把红蓝物体移回收纳区，人把绿色物体放到留用区。',
                  human_targets={'green':'keep_green'},robot_targets={'red':'tray_red','blue':'tray_blue'},
                  tick_hz=15,max_steps=args.ticks_per_activity,activity=None)
    scenarios=[visible_goal_scenario(s,seed=args.seed) for s in [first,second,third]]
    client=WebsocketClientPolicy('127.0.0.1',8765)
    metadata=client.get_server_metadata()
    if metadata.get('action_encoding')!='joint_position':parser.error('本活动流要求位置域学习策略服务')
    instructions=[public_robot_instruction(s,physical=True) for s in scenarios]
    policy=DroidVLAAdapter(client.infer,instruction=instructions[0],execution_horizon=4,action_encoding='joint_position')
    partner=QwenHumanPolicy(first,model_path=args.human_model,persona_id=args.human_persona,
                           decision_interval_steps=15,memory_scope='session')
    directory=args.output_dir/'continuous_activity_stream'
    result=run_activity_stream(scenarios,policy,partner,seed=args.seed,output=directory,
                               backend_factory=factory,instructions=instructions)
    (args.output_dir/'summary.json').write_text(json.dumps({'episodes':[result]},ensure_ascii=False,indent=2))
    (args.output_dir/'provenance.json').write_text(json.dumps({**backend_provenance(args),'policy':args.policy,
        'trained_model':True,'model_server_metadata':metadata,'model_calls':policy.calls,
        'human_persona':args.human_persona,'world_resets':1,'policy_resets':1,'partner_resets':1,
        'purpose':'同一物理世界内更新公开目标和分工，保留双方历史与真实动作状态。',
        'interpretation':'模型操作、人物代理与合成行为效度仍有限，不作为成熟HRC排名。'},ensure_ascii=False,indent=2))
    finalize_video_verification(args.output_dir,required=True)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
