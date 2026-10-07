#!/usr/bin/env python3
"""无机器人协作成绩的神经人策略资格检查；机器人仅经真实控制泊车。"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.libero_native import physical_record,perceived_object_contacts
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
from hrc_pilot.native_contact_human import augment_contact_human
from hrc_pilot.native_grounded_human import GroundedReflectiveHuman
from hrc_pilot.native_autonomous_human import CONTEXTS
from hrc_pilot.native_scene_catalog import CASES,scene_regions
from hrc_pilot.native_activity import public_surfaces
from hrc_pilot.native_execution import NativeMotionObserver
from hrc_pilot.native_personal_evidence import evaluate_personal_goals
from hrc_pilot.native_run_journal import NativeRunJournal,native_time_limits
from hrc_pilot.human_command_delivery import HumanCommandDelivery
from hrc_pilot.native_video_frame import compose_runtime_views
from hrc_pilot.protocol import Observation,Message
from hrc_pilot.video_verification import finalize_video_verification


def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--human-command-delivery',choices=['neural_request','cached_each_tick'],default='neural_request')
    parser.add_argument('--human-policy-architecture',choices=['grounded','deliberative','learned'],default='grounded')
    parser.add_argument('--autonomous-human-context',choices=list(CONTEXTS),default='pantry_work')
    parser.add_argument('--adapter-path',type=Path)
    parser.add_argument('--init-state-id',type=int,default=0);parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--steps',type=int,default=1200);parser.add_argument('--scene-case',choices=list(CASES),default='bowl_on_stove')
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('使用新输出目录')
    model_path=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B')
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free,pci.bus_id','--format=csv,noheader,nounits'],text=True)
    entries={r.split(',')[0].strip():r.split(',') for r in rows.splitlines()};chosen=os.environ.get('CUDA_VISIBLE_DEVICES')
    required=sum(p.stat().st_size for p in model_path.glob('*.safetensors'))//1024**2+8192
    if chosen not in entries or int(entries[chosen][1])<required:parser.error(f'需要单卡{required}MiB余量')
    probe=dict(os.environ);probe.pop('CUDA_VISIBLE_DEVICES',None);probe['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,'scripts/probe_egl_devices.py'],env=probe,text=True))
    matched=[d for d in mapping if d['pci_bus']==entries[chosen][2].strip().lower()[-12:]];assert len(matched)==1
    os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID';os.environ['MUJOCO_EGL_DEVICE_ID']=str(matched[0]['egl_ordinal'])
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    import torch
    paths=[Path(__file__),*sorted(Path('src/hrc_pilot').glob('native*.py')),Path('src/hrc_pilot/llm_human.py'),Path('src/hrc_pilot/human_command_delivery.py'),Path('src/hrc_pilot/learned_human.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    case=CASES[args.scene_case];suite=benchmark.get_benchmark_dict()[case.suite]();task=suite.get_task(case.task_id)
    human_class=GroundedReflectiveHuman;human_kwargs={'reflection_interval_s':6}
    if args.human_policy_architecture=='deliberative':
        from hrc_pilot.native_deliberative_human import DeliberativeArticulatedHuman
        human_class=DeliberativeArticulatedHuman;human_kwargs={}
    if args.human_policy_architecture=='learned':
        from hrc_pilot.learned_human import LearnedArticulatedHuman
        human_class=LearnedArticulatedHuman;human_kwargs={'adapter_path':args.adapter_path}
    human=human_class(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context=args.autonomous_human_context,
        preferred_personal_objects=case.preferred_personal_objects,model_path=model_path,persona_id='independent',
        decision_interval_steps=40,memory_scope='episode',**human_kwargs);human.prepare();human.reset(args.seed);torch.manual_seed(args.seed)
    adapter_hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in args.adapter_path.glob('adapter*') if p.is_file()} if args.adapter_path else {}
    if args.adapter_path:assert human._adapter_loaded and adapter_hashes
    env=OffScreenRenderEnv(bddl_file_name=suite.get_task_bddl_file_path(case.task_id),control_freq=20,
        camera_names=['agentview','robot0_eye_in_hand','frontview'],camera_heights=[256,256,480],camera_widths=[256,256,640],
        **native_time_limits(args.steps,80,True))
    args.output_dir.mkdir(parents=True);ep=args.output_dir/'human_activity';ep.mkdir()
    writer=imageio.get_writer(ep/'demo.mp4',fps=20);timeline=[];trace=[];controls=[];parking=[];journal=NativeRunJournal(ep);delivery=HumanCommandDelivery()
    def frame(t,obs):
        rgb=compose_runtime_views(np.ascontiguousarray(env.sim.render(width=640,height=480,camera_name='hrc_view')[::-1,::-1]),obs,'wide_and_policy')
        writer.append_data(rgb)
        if not timeline:Image.fromarray(rgb).save(ep/'preview.png')
        timeline.append({'frame':len(timeline),'video_time_s':len(timeline)/20,'benchmark_time_s':t,'physics_time_s':float(env.sim.data.time)})
    try:
        env.seed(args.seed);env.reset();states=torch.load(Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file,weights_only=False,map_location='cpu');obs=env.set_init_state(states[args.init_state_id])
        for _ in range(10):obs,*_=env.step([0.]*6+[-1.])
        objects={n:env.sim.data.body_xpos[b].copy() for n,b in env.env.obj_body_id.items()};regions=scene_regions(objects,env.env.objects_dict)
        obs=augment_contact_human(env,regions['near_human'],public_regions=regions,contact_model='articulated_hand')
        actor=NativeArticulatedHuman(env,regions);actor._display(actor.position());env.sim.forward()
        # Real motor parking, not a policy or an object/robot pose write.
        target=np.asarray(obs['robot0_eef_pos']).copy()+[-.15,-.20,.25]
        for step in range(80):
            action=np.r_[np.clip((target-obs['robot0_eef_pos'])*20,-.3,.3),np.zeros(3),-1.]
            parking.append({'physics_time_s':float(env.sim.data.time),'eef_xyz':obs['robot0_eef_pos'].tolist(),'action':action.tolist()})
            frame(None,obs);obs,*_=env.step(action.tolist())
        actor.records.clear();actor.avatar.records.clear()
        (ep/'scene.xml').write_text(env.sim.model.get_xml());messages=[Message('environment','scene_context','The robot is parked and has no active task. Choose your own activity based on your preferences and the measured scene.')]
        context={'context_id':args.autonomous_human_context,'context':CONTEXTS[args.autonomous_human_context],'preferred_personal_objects':human.preferred_personal_objects,
            'regions':regions,'robot_instruction':None,'human_assigned_targets':None,'timed_work_updates':[],'world_initializations':1,'human_policy_resets':1}
        write(ep/'personal_context.json',context);observer=NativeMotionObserver();start=float(env.sim.data.time)
        for step in range(args.steps):
            t=step/20;r=physical_record(env,obs,time_s=t,step=step);motion=observer.update(r);motion['perceived_object_contacts']=perceived_object_contacts(r)
            r.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback(),robot_motion=motion)
            public=Observation(objects={n:tuple(p) for n,p in r['objects'].items()},regions=regions,messages=tuple(messages),robot_ee=tuple(r['robot_ee']),
                human_position=tuple(r['human_position']),held_by_human=(),completed_skills=(),time_s=t,robot_qpos=tuple(r['robot_qpos']),
                human_hand_position=tuple(r['human_hand_position']),human_motor_phase=actor.phase,active_robot_action='native_joint_control',action_phase='native_control',
                human_execution=r['human_execution'],robot_motion=motion,goal_surfaces=public_surfaces(regions),task_family='autonomous_personal_activity',task_description='Choose your own tabletop activity; no robot work is assigned.')
            decision=human.step(public);messages.extend(decision.messages)
            if args.human_command_delivery=='neural_request':delivery.submit(actor,decision.command,len(human.policy_io)-1)
            else:actor.accept(decision.command)
            trace.append(r);frame(t,obs)
            action=[0.]*6+[-1.];before=float(env.sim.data.time);obs,*_=env.step(action)
            controls.append({'step':step,'time_s':t,'action':action,'pre_physics_time_s':before,'post_physics_time_s':float(env.sim.data.time),'actuator_ctrl':env.sim.data.ctrl.tolist(),'source':'calibrated_stationary_robot_no_model'})
            journal.flush({'trace.jsonl':trace,'stationary_robot_control.jsonl':controls,'human_control.jsonl':actor.records,
                'human_avatar.jsonl':actor.avatar.records,'human_policy_io.jsonl':human.policy_io,
                'human_command_delivery.jsonl':delivery.records,**({'human_planner_io.jsonl':human.planning_io} if hasattr(human,'planning_io') else {})})
        r=physical_record(env,obs,time_s=args.steps/20,step=args.steps);r.update(human_hand_position=actor.position().tolist(),human_position=np.r_[actor.body_base,0].tolist(),human_execution=actor.public_feedback());trace.append(r);frame(args.steps/20,obs)
        assert np.isclose(env.sim.data.time-start,args.steps/20,atol=1e-7)
        personal=evaluate_personal_goals(regions,trace,actor.records,human.policy_io,[],require_table_release=True,allow_relative_relations=True)
        result={'scenario':'neural_human_provider_qualification','scene_case':args.scene_case,'human_goal_success':personal['human_current_observable_goals_satisfied'],
            'human_goal_evaluable':personal['human_current_observable_goals_evaluable'],'new_goal_intervals_satisfied':personal['new_target_intervals_with_stable_relation'],
            'personal_evidence':personal,'robot_neural_calls':0,'human_total_neural_inferences':human.audit_state().get('total_neural_inferences',len(human.policy_io)),
            'interpretation':'神经人策略操作资格检查；机器人经真实控制泊车后静止，没有机器人协作成绩或模型排名。'}
        write(ep/'personal_evidence.json',personal);write(ep/'metrics.json',result);write(args.output_dir/'summary.json',{'episodes':[result]})
        journal.flush({'trace.jsonl':trace,'public_dialogue.jsonl':[m.__dict__ for m in messages]})
        write(ep/'parking_control.json',parking);(ep/'model_calls.jsonl').write_text('');(ep/'placement_evidence.jsonl').write_text('')
        write(ep/'video_timeline.json',{'fps':20,'frame_count':len(timeline),'frames':timeline})
    except Exception as error:
        write(args.output_dir/'failure.json',{'status':'failed','error':repr(error),'completed_steps':len(controls)})
        write(ep/'parking_control.json',parking)
        write(ep/'video_timeline.json',{'fps':20,'frame_count':len(timeline),'frames':timeline})
        raise
    finally:writer.close();env.close()
    write(args.output_dir/'provenance.json',{'human_target_source':'model_generated_from_personal_preferences','human_policy_architecture':args.human_policy_architecture,
        'human_model_class':type(human._model).__name__,'human_adapter_sha256':adapter_hashes,
        'human_adapter_files_changed_during_run':[p for p,h in adapter_hashes.items() if sha256(Path(p).read_bytes()).hexdigest()!=h],
        'human_model':str(model_path),'human_adapter':str(args.adapter_path) if args.adapter_path else None,'init_state_id':args.init_state_id,'seed':args.seed,'human_command_delivery':args.human_command_delivery,'robot_policy':'calibration parking then stationary, no neural robot',
        'personal_goal_table_release_required':True,'personal_goal_relative_relations_allowed':True,'source_sha256':hashes,
        'source_files_changed_during_run':[str(p) for p in paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'cuda_visible_devices':chosen,'renderer_device_binding':matched[0]})
    finalize_video_verification(args.output_dir,required=True)
    (args.output_dir/'index.html').write_text('<meta charset="utf-8"><h1>神经人策略操作资格检查</h1><p>前4秒真实泊车；随后人自选目标与动作，非HRC成绩。</p><video controls width="896" src="human_activity/demo.mp4"></video>')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
