#!/usr/bin/env python3
"""真实双相机与末端传感输入的π0.5-LIBERO Genesis运行。"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
from openpi_client.websocket_client_policy import WebsocketClientPolicy

from hrc_pilot.backend_options import add_backend_options, configure_backend, backend_provenance
from hrc_pilot.cartesian_vla_adapter import CartesianVLAAdapter
from hrc_pilot.continuous import run_continuous_episode
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.goal_regions import visible_goal_scenario
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.video_verification import finalize_video_verification
from scripts.collect_contact_demonstrations import ObservingPartner


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend='genesis',experiment_tier='important',robot_grasp_model='friction_contact',render_stride=3)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--ticks',type=int,default=120)
    parser.add_argument('--seed',type=int,default=22)
    parser.add_argument('--object',choices=['red','blue','green'],default='blue')
    args=parser.parse_args()
    args.policy='pi05_libero_pretrained'
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('请使用新输出目录')
    client=WebsocketClientPolicy('127.0.0.1',args.port)
    metadata=client.get_server_metadata()
    if metadata.get('config')!='pi05_libero':parser.error('服务未声明LIBERO接口')
    factory=configure_backend(args,parser,args.output_dir)
    active={}
    def backend(scenario):
        world=factory(scenario)
        active['workspace']=world.workspace
        # Published LIBERO Panda resting joint pose; set only during initialization.
        world.workspace.home=np.array([0,-0.161037389,0,-2.44459747,0,2.22675220,np.pi/4,0.04,0.04])
        return world
    instruction=f'Pick up the {args.object} block and place it on the blue mat.'
    scenario=replace(make_history_probe(),name='pi05_libero_'+args.object,tick_hz=20,max_steps=args.ticks,
                     human_targets={},robot_targets={args.object:'tray_'+args.object},activity=None,description=instruction)
    scenario=visible_goal_scenario(scenario,seed=args.seed)
    policy=CartesianVLAAdapter(client.infer,lambda:active['workspace'].robot,instruction=instruction)
    result=run_continuous_episode(scenario,policy,ObservingPartner(scenario),seed=args.seed,
                                  output=args.output_dir/scenario.name,backend_factory=backend,partner_mode='observing')
    (args.output_dir/'summary.json').write_text(json.dumps({'episodes':[result]},ensure_ascii=False,indent=2))
    provenance={**backend_provenance(args),'policy':args.policy,'trained_model':True,'model_server_metadata':metadata,
                'model_calls':policy.calls,'control_hz':20,'execution_horizon':5,
                'pose_frame_translation':[-0.56,0,0],'tcp_offset_m':[0,0,0.1034],
                'purpose':'仿真预训练策略的实际末端控制接口运行；先验证传感与动作约定。',
                'interpretation':'Genesis与原LIBERO的相机、坐标和接触分布尚未完成匹配校准；当前不能用于模型能力排名或HRC结论。'}
    (args.output_dir/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    finalize_video_verification(args.output_dir,required=True)
    print(write_continuous_report(args.output_dir,[result]),flush=True)


if __name__=='__main__':main()
