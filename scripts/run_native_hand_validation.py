#!/usr/bin/env python3
"""单独校准双指真实接触抓放，不将校准教师计作Benchmark模型策略。"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.continuous import HumanCommand
from hrc_pilot.libero_native import physical_record
from hrc_pilot.native_contact_human import augment_contact_human
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
from hrc_pilot.native_activity import activity_regions
from hrc_pilot.video_verification import finalize_video_verification


def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def lines(path,records):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=600);parser.add_argument('--object-id',default='cookies_1')
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('使用新输出目录')
    chosen=os.environ.get('CUDA_VISIBLE_DEVICES')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free,pci.bus_id','--format=csv,noheader,nounits'],text=True)
    entries={r.split(',')[0].strip():r.split(',') for r in gpu.splitlines()}
    if chosen not in entries or int(entries[chosen][1])<4096:parser.error('需要单卡至少4GB空闲显存')
    probe=dict(os.environ);probe.pop('CUDA_VISIBLE_DEVICES',None);probe['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,'scripts/probe_egl_devices.py'],env=probe,text=True))
    matched=[d for d in mapping if d['pci_bus']==entries[chosen][2].strip().lower()[-12:]]
    assert len(matched)==1;os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID';os.environ['MUJOCO_EGL_DEVICE_ID']=str(matched[0]['egl_ordinal'])
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    import torch
    paths=[Path(__file__),Path('src/hrc_pilot/native_articulated_hand.py'),Path('src/hrc_pilot/native_contact_human.py'),Path('src/hrc_pilot/native_avatar.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    suite=benchmark.get_benchmark_dict()['libero_spatial']();task=suite.get_task(2)
    env=OffScreenRenderEnv(bddl_file_name=suite.get_task_bddl_file_path(2),control_freq=20,
        camera_names=['agentview','robot0_eye_in_hand','frontview'],camera_heights=[256,256,480],camera_widths=[256,256,640])
    args.output_dir.mkdir(parents=True);episode=args.output_dir/'hand_validation';episode.mkdir()
    writer=imageio.get_writer(episode/'demo.mp4',fps=20);trace=[];timeline=[];teacher=[]
    def frame(time):
        rgb=np.ascontiguousarray(env.sim.render(width=640,height=480,camera_name='hrc_view')[::-1,::-1]);writer.append_data(rgb)
        if not timeline:Image.fromarray(rgb).save(episode/'preview.png')
        timeline.append({'frame':len(timeline),'video_time_s':len(timeline)/20,'benchmark_time_s':time,'physics_time_s':float(env.sim.data.time)})
    try:
        env.seed(0);env.reset();states=torch.load(Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file,weights_only=False,map_location='cpu')
        obs=env.set_init_state(states[0])
        for _ in range(10):obs,*_=env.step([0.]*6+[-1.])
        objects={n:env.sim.data.body_xpos[b].copy() for n,b in env.env.obj_body_id.items()};regions=activity_regions(objects)
        regions['cookies_shelf']=(.32,.40,float(objects[args.object_id][2])+.08)
        obs=augment_contact_human(env,regions['plate_ready'],public_regions=regions,contact_model='articulated_hand',raised_storage=True)
        actor=NativeArticulatedHuman(env,regions);actor._display(actor.position());env.sim.forward();env.env._update_observables(force=True);obs=env.env._get_observations()
        (episode/'scene.xml').write_text(env.sim.model.get_xml());initial=actor.object_position(args.object_id).copy();start=float(env.sim.data.time)
        actor.accept(HumanCommand('grasp',args.object_id));teacher.append({'time_s':0.,'intent':'grasp','object_id':args.object_id})
        placed=False
        for step in range(args.steps):
            t=step/20;record=physical_record(env,obs,time_s=t,step=step)
            record.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback())
            trace.append(record);frame(t)
            if actor.phase=='holding' and not placed:
                actor.accept(HumanCommand('place',args.object_id,'cookies_shelf'));placed=True
                teacher.append({'time_s':t,'intent':'place','object_id':args.object_id,'destination':'cookies_shelf'})
            obs,*_=env.step([0.]*6+[-1.])
            assert np.isclose(env.sim.data.time-start,(step+1)/20,atol=1e-7)
        record=physical_record(env,obs,time_s=args.steps/20,step=args.steps)
        record.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback())
        trace.append(record);frame(args.steps/20)
        lines(episode/'trace.jsonl',trace);lines(episode/'human_control.jsonl',actor.records);lines(episode/'human_avatar.jsonl',actor.avatar.records)
        write(episode/'video_timeline.json',{'fps':20,'frame_count':len(timeline),'frames':timeline});write(episode/'teacher_commands.json',teacher)
        final=actor.object_position(args.object_id);target=np.asarray(regions['cookies_shelf'])
        result={'scenario':'native_hand_friction_lift_and_elevated_release','object_id':args.object_id,
                'initial_object_xyz':initial.tolist(),'final_object_xyz':final.tolist(),'target_xyz':target.tolist(),
                'maximum_object_lift_m':max(r['objects'][args.object_id][2]-initial[2] for r in trace),
                'human_peak_speed_m_s':max(float(np.linalg.norm(r['actual_velocity'])) for r in actor.records),
                'motor_failure':actor.motor_failure,'terminal_phase':actor.phase,'teacher_place_command_issued':placed,
                'interpretation':'独立真实抓放执行器校准；机器人原地，命令来自校准教师，不能算生成式人或HRC成功。'}
        write(episode/'metrics.json',result);write(args.output_dir/'summary.json',{'episodes':[result]})
    finally:writer.close();env.close()
    write(args.output_dir/'provenance.json',{'backend':'LIBERO_MuJoCo_native','trained_model':False,'human_policy':'calibration_teacher',
        'source_sha256':hashes,'source_files_changed_during_run':[str(p) for p in paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'human_contact_model':'articulated_hand','cuda_visible_devices':chosen,'renderer_device_binding':matched[0],'object_pose_writes_during_control':0})
    finalize_video_verification(args.output_dir,required=True)
    (args.output_dir/'index.html').write_text('<meta charset="utf-8"><h1>真实接触手校准</h1><p>非学习策略与HRC成绩；请查看接触、抬起和释放审计。</p><video controls width="800" src="hand_validation/demo.mp4"></video>')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
