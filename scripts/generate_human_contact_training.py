#!/usr/bin/env python3
"""真实接触教师生成输入／动作同stem范例；不计作神经Benchmark结果。"""
import argparse
from dataclasses import asdict,replace
from hashlib import sha256
import json,os,subprocess,sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.protocol import Observation,Message
from hrc_pilot.libero_native import physical_record,perceived_object_contacts
from hrc_pilot.native_contact_human import augment_contact_human
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
from hrc_pilot.native_scene_catalog import CASES,scene_regions
from hrc_pilot.native_execution import NativeMotionObserver
from hrc_pilot.native_activity import public_surfaces
from hrc_pilot.native_run_journal import NativeRunJournal,native_time_limits
from hrc_pilot.native_video_frame import compose_runtime_views
from hrc_pilot.video_verification import finalize_video_verification
from hrc_pilot.human_command_delivery import HumanCommandDelivery
from hrc_pilot.human_training_teacher import ContactDemonstrationTeacher
from hrc_pilot.learned_human import LearnedArticulatedHuman


def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--scene-cases',nargs='+',choices=list(CASES),default=['food_into_bowl','drawer_access'])
    parser.add_argument('--init-state-ids',nargs='+',type=int,default=[0,1,2,3])
    parser.add_argument('--orders',nargs='+',type=int,default=[0,1])
    parser.add_argument('--steps',type=int,default=1200)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('输出需为新目录')
    entries={r.split(',')[0].strip():r.split(',') for r in subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free,pci.bus_id','--format=csv,noheader,nounits'],text=True).splitlines()}
    selected=os.environ.get('CUDA_VISIBLE_DEVICES')
    if selected not in entries or int(entries[selected][1])<4096:parser.error('需单卡至少4GB空闲显存')
    probe=dict(os.environ);probe.pop('CUDA_VISIBLE_DEVICES',None);probe['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,'scripts/probe_egl_devices.py'],env=probe,text=True))
    device=next(d for d in mapping if d['pci_bus']==entries[selected][2].strip().lower()[-12:])
    os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID';os.environ['MUJOCO_EGL_DEVICE_ID']=str(device['egl_ordinal'])
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    import torch
    paths=[Path(__file__),*Path('src/hrc_pilot').glob('native*.py'),Path('src/hrc_pilot/learned_human.py'),Path('src/hrc_pilot/human_training_teacher.py'),Path('src/hrc_pilot/human_command_delivery.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output_dir.mkdir(parents=True);results=[]
    for key in args.scene_cases:
        case=CASES[key];suite=benchmark.get_benchmark_dict()[case.suite]();task=suite.get_task(case.task_id)
        states=torch.load(Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file,weights_only=False,map_location='cpu')
        for initial_id in args.init_state_ids:
            for order in args.orders:
                name=f'{key}__init{initial_id:03d}__order{order}';ep=args.output_dir/'episodes'/name;ep.mkdir(parents=True)
                env=OffScreenRenderEnv(bddl_file_name=suite.get_task_bddl_file_path(case.task_id),control_freq=20,
                    camera_names=['agentview','robot0_eye_in_hand','frontview'],camera_heights=[256,256,480],camera_widths=[256,256,640],**native_time_limits(args.steps,80,True))
                trace=[];teacher_io=[];timeline=[];parking=[];controls=[];journal=NativeRunJournal(ep);delivery=HumanCommandDelivery()
                writer=imageio.get_writer(ep/'demo.mp4',fps=20)
                def frame(t,obs):
                    rgb=compose_runtime_views(np.ascontiguousarray(env.sim.render(width=640,height=480,camera_name='hrc_view')[::-1,::-1]),obs,'wide_and_policy')
                    writer.append_data(rgb)
                    if not timeline:Image.fromarray(rgb).save(ep/'preview.png')
                    timeline.append({'frame':len(timeline),'video_time_s':len(timeline)/20,'benchmark_time_s':t,'physics_time_s':float(env.sim.data.time)})
                try:
                    env.seed(initial_id);env.reset();obs=env.set_init_state(states[initial_id])
                    for _ in range(10):obs,*_=env.step([0.]*6+[-1.])
                    objects={n:env.sim.data.body_xpos[b].copy() for n,b in env.env.obj_body_id.items()};regions=scene_regions(objects,env.env.objects_dict)
                    obs=augment_contact_human(env,regions['near_human'],public_regions=regions,contact_model='articulated_hand');actor=NativeArticulatedHuman(env,regions);actor._display(actor.position());env.sim.forward()
                    park=np.asarray(obs['robot0_eef_pos'])+[-.15,-.20,.25]
                    for step in range(80):
                        action=np.r_[np.clip((park-obs['robot0_eef_pos'])*20,-.3,.3),np.zeros(3),-1.]
                        parking.append({'physics_time_s':float(env.sim.data.time),'action':action.tolist()});frame(None,obs);obs,*_=env.step(action.tolist())
                    actor.records.clear();actor.avatar.records.clear();(ep/'scene.xml').write_text(env.sim.model.get_xml())
                    names=['akita_black_bowl_1','wine_bottle_1'] if key=='food_into_bowl' else ['cream_cheese_1','wine_bottle_1']
                    if order:names.reverse()
                    targets=[{'object_id':n,'destination':n+'_personal'} for n in names];teacher=ContactDemonstrationTeacher(targets)
                    formatter=LearnedArticulatedHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='shared_meal',
                        preferred_personal_objects=names,model_path=Path('/unused'),persona_id='independent',decision_interval_steps=40,memory_scope='episode')
                    formatter.reset(initial_id);formatter.personal_targets=targets;formatter.long_term_intention='将偏好物品整理到各自个人区域并维持布置'
                    messages=[Message('environment','scene_context','The robot is parked and has no active task. Choose your own activity based on your preferences and the measured scene.')]
                    observer=NativeMotionObserver();start=float(env.sim.data.time)
                    decision_id=-1;command=None
                    for step in range(args.steps):
                        t=step/20;r=physical_record(env,obs,time_s=t,step=step);motion=observer.update(r);motion['perceived_object_contacts']=perceived_object_contacts(r)
                        r.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback(),robot_motion=motion)
                        teacher.observe(r,regions)
                        if step%40==0:
                            public=Observation(objects={n:tuple(v) for n,v in r['objects'].items()},regions=regions,messages=tuple(messages),robot_ee=tuple(r['robot_ee']),
                                human_position=tuple(r['human_position']),held_by_human=(),completed_skills=(),time_s=t,robot_qpos=tuple(r['robot_qpos']),human_hand_position=tuple(r['human_hand_position']),human_motor_phase=actor.phase,
                                active_robot_action='native_joint_control',action_phase='native_control',human_execution=r['human_execution'],robot_motion=motion,goal_surfaces=public_surfaces(regions),task_family='autonomous_personal_activity',task_description='Choose your own tabletop activity; no robot work is assigned.')
                            prompt=formatter._prompt(public);label=teacher.decision(public);command=formatter._validated_command(label,public);decision_id+=1
                            formatter.public_decision_history.append({'time_s':t,**{k:label[k] for k in ['intent','object_id','destination']}})
                            accepted=asdict(command);stem=f'{name}__step{step:06d}';split='dev' if initial_id==3 else 'train';folder=args.output_dir/'samples'/split;folder.mkdir(parents=True,exist_ok=True)
                            source={'system_prompt':formatter._system_prompt(),'public_input':prompt,'episode_id':name,'time_s':t,'source':'geometry_teacher_actual_contact_rollout'}
                            write(folder/(stem+'.source.json'),source);write(folder/(stem+'.target.json'),label)
                            teacher_io.append({'time_s':t,'decision_id':decision_id,'requested':label,'accepted':accepted,'command_validation':formatter.last_command_feedback})
                        delivery.submit(actor,command,decision_id);trace.append(r);frame(t,obs);before=float(env.sim.data.time);obs,*_=env.step([0.]*6+[-1.])
                        controls.append({'step':step,'time_s':t,'pre_physics_time_s':before,'post_physics_time_s':float(env.sim.data.time),'action':[0.]*6+[-1.]})
                        journal.flush({'trace.jsonl':trace,'human_control.jsonl':actor.records,'human_avatar.jsonl':actor.avatar.records,'teacher_io.jsonl':teacher_io,'human_command_delivery.jsonl':delivery.records,'stationary_robot_control.jsonl':controls})
                    r=physical_record(env,obs,time_s=args.steps/20,step=args.steps);r.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback());trace.append(r);frame(args.steps/20,obs)
                    assert np.isclose(env.sim.data.time-start,args.steps/20,atol=1e-7)
                    journal.flush({'trace.jsonl':trace});write(ep/'video_timeline.json',{'fps':20,'frame_count':len(timeline),'frames':timeline});write(ep/'parking_control.json',parking)
                    result={'episode_id':name,'targets':targets,'terminal_released_stable_targets':[obj for obj,dwell in teacher.dwell.items() if dwell>=.2-1e-9],
                        'teacher_decisions':len(teacher_io),'actual_neural_calls':0,'role':'data_generation_only','split':'dev' if initial_id==3 else 'train'}
                    write(ep/'metrics.json',result);results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
                finally:writer.close();env.close()
    write(args.output_dir/'summary.json',{'episodes':results});write(args.output_dir/'provenance.json',{'role':'data_generation_only','trained_model':False,'actual_neural_calls':0,
        'source_sha256':hashes,'source_files_changed_during_run':[str(p) for p in paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'pair_rule':'same stem .source.json / .target.json','split_rule':'entire init3 episodes dev, init0-2 train; no frame random split',
        'cuda_visible_devices':selected,'renderer_device_binding':device})
    finalize_video_verification(args.output_dir,required=True)


if __name__=='__main__':main()
