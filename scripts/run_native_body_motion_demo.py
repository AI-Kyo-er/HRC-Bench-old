#!/usr/bin/env python3
"""仅验证完整人物退让/返回与接触手连接；脚本命令不是人类策略成绩。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.native_contact_human import augment_contact_human,NativeContactHuman
from hrc_pilot.continuous import HumanCommand
from hrc_pilot.video_verification import finalize_video_verification


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('请用新输出目录')
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free,pci.bus_id','--format=csv,noheader,nounits'],text=True)
    cards={r.split(',')[0].strip():(int(r.split(',')[1]),r.split(',')[2].strip().lower()[-12:]) for r in rows.splitlines()}
    selected=os.environ.get('CUDA_VISIBLE_DEVICES')
    if selected not in cards or cards[selected][0]<4096:parser.error('需选定单张空闲4GiB以上GPU')
    probe=dict(os.environ);probe.pop('CUDA_VISIBLE_DEVICES',None);probe['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,str(Path(__file__).with_name('probe_egl_devices.py'))],env=probe,text=True))
    device=next(r for r in mapping if r['pci_bus']==cards[selected][1])
    os.environ['MUJOCO_EGL_DEVICE_ID']=str(device['egl_ordinal']);os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    import torch
    suite=benchmark.get_benchmark_dict()['libero_spatial']();task=suite.get_task(0)
    env=OffScreenRenderEnv(bddl_file_name=suite.get_task_bddl_file_path(0),render_gpu_device_id=0,
                          camera_heights=256,camera_widths=256)
    directory=args.output_dir/'body_clearance_and_return';directory.mkdir(parents=True)
    writer=imageio.get_writer(directory/'demo.mp4',fps=20)
    frames=[];trace=[];returning=False
    try:
        env.seed(30);env.reset()
        state_path=Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file
        states=torch.load(state_path,weights_only=False,map_location='cpu');env.set_init_state(states[0])
        for _ in range(10):obs,_,_,_=env.step([0.]*6+[-1.])
        plate=env.sim.data.body_xpos[env.env.obj_body_id['plate_1']].copy()
        obs=augment_contact_human(env,plate+[0,.12,0],visualization='vico_skin')
        actor=NativeContactHuman(env,{'near_human':tuple(plate+[0,.12,0])})
        actor._display(actor.position());env.sim.forward();env.env._update_observables(force=True)
        for step in range(160):
            if actor.body_base[1]>.94:returning=True
            actor.accept(HumanCommand('return' if returning else 'away'))
            pixels=np.ascontiguousarray(env.sim.render(width=640,height=480,camera_name='hrc_view')[::-1,::-1])
            writer.append_data(pixels)
            if step==0:Image.fromarray(pixels).save(directory/'preview.png')
            frames.append({'video_time_s':step/20,'benchmark_time_s':step/20})
            trace.append({'time_s':step/20,'body_position':actor.body_base.tolist(),'hand_position':actor.position().tolist()})
            obs,_,_,_=env.step([0.]*6+[-1.])
        metric={'scenario':'body_clearance_and_return','task_success':bool(returning and abs(actor.body_base[1]-.60)<.01),
                'maximum_body_y':max(row['body_position'][1] for row in trace),
                'final_body_position':actor.body_base.tolist(),
                'avatar_maximum_alignment_error_m':max(row['alignment_error_m'] for row in actor.avatar.records),
                'interpretation':'仅运动执行器验证，离返命令由脚本给出；机器人保持末端，未测试人类策略或HRC能力。'}
        (directory/'metrics.json').write_text(json.dumps(metric,ensure_ascii=False,indent=2))
        (directory/'trace.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in trace))
        (directory/'human_avatar.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in actor.avatar.records))
        (directory/'human_control.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in actor.records))
        (directory/'video_timeline.json').write_text(json.dumps({'fps':20,'frame_count':len(frames),'frames':frames}))
        (args.output_dir/'summary.json').write_text(json.dumps({'episodes':[metric]},ensure_ascii=False,indent=2))
        (args.output_dir/'provenance.json').write_text(json.dumps({'trained_model':False,'human_policy':'motor_calibration_commands',
                'renderer_device_binding':device,'avatar_assets':actor.avatar.rig.metadata,'robot_actions':'no_op_osc',
                'purpose':'检查真实Sim中的骨骼步行、清离与返回，动作没有瞬间位移。'},ensure_ascii=False,indent=2))
        print(metric,flush=True)
    finally:writer.close();env.close()
    finalize_video_verification(args.output_dir,required=True)
    (args.output_dir/'index.html').write_text('<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><h1>完整人物运动执行器验证</h1><p>只测试脚本发出的退让和返回命令落到真实场景，不作为人类策略或机器人模型成绩。</p><video style="width:100%;max-width:960px" controls src="body_clearance_and_return/demo.mp4"></video></html>')


if __name__=='__main__':main()
