#!/usr/bin/env python3
"""在线生成式人＋真实VLA的持续共同活动；显式分开公开与私有输入。"""
import argparse
from collections import deque
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.joint_activity import ACTIVITIES,PROFILES
from hrc_pilot.joint_human_policy import JointHumanPolicy
from hrc_pilot.kinematic_human import KinematicHuman
from hrc_pilot.libero_native import native_policy_input,input_audit,physical_record
from hrc_pilot.native_contact_human import augment_contact_human
from hrc_pilot.native_scene_catalog import CASES,resolve_goal,scene_regions
from hrc_pilot.native_goal_evidence import create_goal_evidence,goal_success
from hrc_pilot.native_run_journal import NativeRunJournal,native_time_limits
from hrc_pilot.native_video_frame import compose_runtime_views
from hrc_pilot.video_verification import finalize_video_verification
from hrc_pilot.protocol import Message


def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2))


def robot_prompt(activity,dialogue):
    # 只转发已经公开的实际表达，不翻译私人意图，不判断下一步任务。
    spoken='\n'.join(f'{m["speaker"]}: {m["text"]}' for m in dialogue[-12:])
    return activity.public_description+'\nActual public conversation:\n'+spoken


def evaluate_chain(activity,trace,human,controls,placement):
    changes=[]
    for a,b in zip(human,human[1:]):
        if a['choice'].get('intention')!=b['choice'].get('intention'):
            changes.append({'time_s':b['time_s'],'before':a['choice'].get('intention'),
                'after':b['choice'].get('intention'),'reason':b['choice'].get('reason'),
                'interpretation':'文字变化待结合行为判断，不当作语义重组计数'})
    first=next((r['time_s'] for r in placement if goal_success(r)),None)
    completion_times={}
    for r in trace:
        for i in r['human_execution']['completed_requests']:
            if i<len(human) and human[i]['choice']['action']=='place':completion_times.setdefault(i,r['time_s'])
    completed=[(t,i) for i,t in completion_times.items()]
    prepared=sorted({t for t,i in completed if first is None or t<first})
    after=sorted({t for t,i in completed if first is not None and t>first})
    robot_final=goal_success(placement[-1]) if placement else False
    return {'activity':activity.key,'robot_native_goal_first_stable_s':first,'robot_native_goal_terminal':robot_final,
        'human_explicit_pick_calls':sum(d['choice']['action']=='pick' for d in human),
        'human_explicit_place_calls':sum(d['choice']['action']=='place' for d in human),
        'human_completed_place_before_native_goal_times_s':prepared[:1],
        'human_completed_place_after_native_goal_times_s':after[:1],
        'human_intention_text_changes_for_review':changes,'human_neural_calls':len(human),
        'robot_actual_control_steps':len(controls),'world_initializations':1,
        'activity_completion_status':'requires_semantic_and_physical_review',
        'interpretation':'记录机器人原生贡献及人明确动作的时间见证；尚未以原生任务或文字变化冒充完整活动成功。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activity',choices=list(ACTIVITIES),required=True)
    parser.add_argument('--profile',choices=list(PROFILES),default='participating')
    parser.add_argument('--init-state-id',type=int,default=0);parser.add_argument('--seed',type=int,default=50)
    parser.add_argument('--steps',type=int,default=1600);parser.add_argument('--context-step',type=int,default=800)
    parser.add_argument('--port',type=int,default=8766);parser.add_argument('--coordinator-port',type=int)
    parser.add_argument('--human-model',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B'))
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists():parser.error('正式运行必须使用新目录，不能覆盖已有证据')
    entries={r.split(',')[0].strip():r.split(',') for r in subprocess.check_output(
        ['nvidia-smi','--query-gpu=index,memory.free,pci.bus_id','--format=csv,noheader,nounits'],text=True).splitlines()}
    chosen=os.environ.get('CUDA_VISIBLE_DEVICES')
    required=sum(p.stat().st_size for p in args.human_model.glob('*.safetensors'))//1024**2+8192
    if chosen not in entries or int(entries[chosen][1])<required:parser.error(f'需要单卡{required}MiB空闲显存')
    probe=dict(os.environ);probe.pop('CUDA_VISIBLE_DEVICES',None);probe['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,'scripts/probe_egl_devices.py'],env=probe,text=True))
    device=next(d for d in mapping if d['pci_bus']==entries[chosen][2].strip().lower()[-12:])
    os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID';os.environ['MUJOCO_EGL_DEVICE_ID']=str(device['egl_ordinal'])
    from libero.libero import benchmark,get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    from openpi_client.websocket_client_policy import WebsocketClientPolicy
    from hrc_pilot.robot_coordination import CoordinatorClient,coordination_request,hold_actions
    import torch
    torch.manual_seed(args.seed)
    activity=ACTIVITIES[args.activity];case=CASES[activity.scene_case]
    suite=benchmark.get_benchmark_dict()[case.suite]();task=suite.get_task(case.task_id)
    states=torch.load(Path(get_libero_path('init_states'))/task.problem_folder/task.init_states_file,
                      map_location='cpu',weights_only=False)
    human=JointHumanPolicy(activity,model_path=args.human_model,profile=args.profile,seed=args.seed);human.prepare()
    client=WebsocketClientPolicy('127.0.0.1',args.port)
    coordinator=CoordinatorClient(args.coordinator_port) if args.coordinator_port else None
    paths=[Path(__file__),Path('src/hrc_pilot/joint_activity.py'),Path('src/hrc_pilot/joint_human_policy.py'),
           Path('src/hrc_pilot/kinematic_human.py'),Path('src/hrc_pilot/llm_human.py'),
           *Path('src/hrc_pilot').glob('native*.py'),Path('src/hrc_pilot/robot_coordination.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output_dir.mkdir(parents=True);ep=args.output_dir/'episode';ep.mkdir();journal=NativeRunJournal(ep)
    env=OffScreenRenderEnv(bddl_file_name=suite.get_task_bddl_file_path(case.task_id),control_freq=20,
        camera_names=['agentview','robot0_eye_in_hand','frontview'],camera_heights=[256,256,480],
        camera_widths=[256,256,640],**native_time_limits(args.steps,10,True))
    writer=imageio.get_writer(ep/'demo.mp4',fps=20)
    trace=[];controls=[];calls=[];plans=[];timeline=[];events=[];action_plan=deque()
    dialogue=[{'time_s':0.,'speaker':'environment','kind':'activity','text':activity.public_description}]
    private_context=[];initial_image=None;last_plan=None;held_gripper=None
    def frame(t,obs):
        rgb=compose_runtime_views(np.ascontiguousarray(env.sim.render(width=640,height=480,camera_name='hrc_view')[::-1,::-1]),obs,'wide_and_policy')
        writer.append_data(rgb)
        if not timeline:Image.fromarray(rgb).save(ep/'preview.png')
        timeline.append({'frame':len(timeline),'video_time_s':len(timeline)/20,
            'benchmark_time_s':t,'physics_time_s':float(env.sim.data.time)})
    try:
        env.seed(args.seed);env.reset();obs=env.set_init_state(states[args.init_state_id])
        for _ in range(10):obs,*_=env.step([0.]*6+[-1.])
        regions=scene_regions({n:env.sim.data.body_xpos[b].copy() for n,b in env.env.obj_body_id.items()},env.env.objects_dict)
        if 'akita_black_bowl_1' in env.env.obj_body_id:
            regions['serving_ready']=tuple(env.sim.data.body_xpos[env.env.obj_body_id['akita_black_bowl_1']]+[0,.10,0])
            regions['snack_delivery']=regions['akita_black_bowl_1_personal']
        if 'wine_bottle_1' in env.env.obj_body_id:regions['drink_staging']=regions['wine_bottle_1_home']
        if args.activity=='drawer_access':
            # 实测抽屉支撑位置在后续每步更新，不能由人文字宣称开好。
            middle=next((b for n,b in env.env.obj_body_id.items() if 'cabinet' in n),None)
            if middle is not None:regions['drawer_storage']=tuple(env.sim.data.body_xpos[middle]+[0,-.15,.08])
        obs=augment_contact_human(env,regions['near_human'],public_regions=regions,contact_model='fingertip')
        actor=KinematicHuman(env,regions);actor._display(actor.position());env.sim.forward()
        (ep/'scene.xml').write_text(env.sim.model.get_xml())
        write(ep/'task.json',{'public_activity':activity.public(),'native_robot_task':task.language,
            'private_human_background':activity.private_background,'profile':args.profile,'regions':regions})
        placement=create_goal_evidence(resolve_goal(env));start=float(env.sim.data.time)
        previous=None
        for step in range(args.steps):
            t=step/20;r=physical_record(env,obs,time_s=t,step=step)
            feedback=actor.public_feedback()
            r.update(human_hand_position=actor.position().tolist(),human_body_xy=actor.body_base.tolist(),human_execution=feedback)
            if step==args.context_step:
                context={'time_s':t,'source':'external_private_context','text':activity.external_context,
                         'interpretation':'外部需要通知，不指定人的意图或动作'}
                private_context.append(context);events.append(context)
            if step%40==0:
                speed=0. if previous is None else float(np.linalg.norm(np.asarray(r['robot_ee'])-previous['robot_ee'])*20)
                scene={'time_s':t,'objects_xyz':r['objects'],'regions_xyz':regions,
                    'robot_eef_xyz':r['robot_ee'],'robot_motion':{'eef_speed_m_s':speed},
                    'fixture_joints':r['articulated_joints'],'own_execution':feedback,
                    'public_dialogue':dialogue[-16:],'private_context':private_context[-3:],
                    'action_interface':{'actions':['pick','place','point','move_hand','away','return','wait'],
                        'hand_workspace_xyz_min':[-.7,-.4,.95],'hand_workspace_xyz_max':[.7,.9,1.5],
                        'place_destination_names':list(regions),'held_object':actor.held}}
                d=human.decide(scene);actor.accept_choice(d['choice'],d['decision_id'])
                if d['choice'].get('message'):
                    dialogue.append({'time_s':t,'speaker':'human','kind':d['choice'].get('message_kind','notice'),
                        'text':d['choice']['message'],'human_decision_id':d['decision_id']})
                    # 新的公开表达使机器人重新观察；不选择其响应动作。
                    action_plan.clear()
                print(json.dumps({'step':step,'human_choice':d['choice'],'parse_error':d['parse_error']},ensure_ascii=False),flush=True)
            trace.append(r);frame(t,obs)
            if not action_plan:
                instruction=robot_prompt(activity,dialogue)
                source='actual_vla_public_dialogue';request=native_policy_input(obs,instruction)
                if coordinator and (step%40==0 or last_plan is None):
                    if initial_image is None:initial_image=request['observation/image'].copy()
                    public_request=coordination_request(time_s=t,robot_task=activity.public_description,
                        human_task='Human chooses their participation and intent; infer only from visible actions and public speech.',
                        dialogue=[Message(m['speaker'],m['kind'],m['text']) for m in dialogue],
                        state=request['observation/state'],images={'initial':initial_image,'current':request['observation/image'],'wrist':request['observation/wrist_image']},
                        history=[p['decision'] for p in plans],current_goal=last_plan['decision']['current_goal'] if last_plan else '',
                        self_execution={'actual_control_steps':len(controls),'eef_xyz':r['robot_ee'],
                            'last_action':controls[-1]['action'] if controls else None})
                    last_plan=coordinator.infer(public_request);last_plan.update(time_s=t,decision_id=len(plans));plans.append(last_plan)
                    if last_plan['decision']['message']:
                        dialogue.append({'time_s':t,'speaker':'robot','kind':'response','text':last_plan['decision']['message']})
                if coordinator:
                    selected=last_plan['decision']
                    if selected['mode']=='move_ee':
                        # 本入口仅支持VLA操作／保持，非法模式明确拒绝，不隐蔽增加低层教师。
                        source='coordinator_unsupported_action_hold';response={'actions':hold_actions(request['observation/state'],10,held_gripper)}
                    elif selected['mode']=='hold':
                        source='coordinator_selected_hold';response={'actions':hold_actions(request['observation/state'],10,held_gripper)}
                    else:
                        request=native_policy_input(obs,selected['instruction']);response=client.infer(request)
                        source='actual_vla_coordinator_instruction'
                else:response=client.infer(request)
                chunk=np.asarray(response['actions'],dtype=float)
                if chunk.ndim!=2 or chunk.shape[1]!=7 or not np.isfinite(chunk).all():raise ValueError('VLA动作必须是有限N×7')
                count=min(10,len(chunk));stem=f'observation_{step:06d}'
                Image.fromarray(request['observation/image']).save(ep/(stem+'.png'))
                Image.fromarray(request['observation/wrist_image']).save(ep/(stem+'_wrist.png'))
                np.save(ep/(stem+'_state.npy'),request['observation/state'])
                np.save(ep/(stem+'_actions.npy'),chunk[:count])
                call={'call_id':len(calls),'time_s':t,'step':step,'action_source':source,
                    'visible_dialogue_count':len(dialogue),'prompt':request['prompt'],**input_audit(request),
                    'raw_action_chunk':chunk.tolist(),'executed_action_count':count,
                    'coordinator_decision_id':last_plan['decision_id'] if last_plan else None}
                calls.append(call);action_plan.extend(chunk[:count])
            action=action_plan.popleft();before=float(env.sim.data.time)
            obs,*_=env.step(action.tolist());held_gripper=float(action[-1])
            current=physical_record(env,obs,time_s=(step+1)/20,step=step+1)
            placement.update(r,current,bool(env.check_success()))
            controls.append({'step':step,'time_s':t,'action':action.tolist(),'model_call_id':calls[-1]['call_id'],
                'source':calls[-1]['action_source'],'pre_physics_time_s':before,'post_physics_time_s':float(env.sim.data.time)})
            journal.flush({'trace.jsonl':trace,'human_policy_io.jsonl':human.decisions,
                'human_control.jsonl':actor.records,'human_command_receipts.jsonl':actor.receipts,
                'robot_control.jsonl':controls,'model_calls.jsonl':calls,'robot_planner_io.jsonl':plans,
                'public_dialogue.jsonl':dialogue,'private_context.jsonl':events,'placement_evidence.jsonl':placement.records})
            previous=r
        r=physical_record(env,obs,time_s=args.steps/20,step=args.steps)
        r.update(human_hand_position=actor.position().tolist(),human_body_xy=actor.body_base.tolist(),human_execution=actor.public_feedback())
        trace.append(r);frame(args.steps/20,obs);journal.flush({'trace.jsonl':trace})
        assert np.isclose(env.sim.data.time-start,args.steps/20,atol=1e-7)
        result=evaluate_chain(activity,trace,human.decisions,controls,placement.records)
        result.update(init_state_id=args.init_state_id,seed=args.seed,role='development_joint_activity_run')
        write(ep/'metrics.json',result);write(args.output_dir/'summary.json',{'episodes':[result]})
    except BaseException as error:
        write(args.output_dir/'failure.json',{'error':repr(error),'completed_control_steps':len(controls)})
        raise
    finally:
        writer.close();env.close()
        write(ep/'video_timeline.json',{'fps':20,'frame_count':len(timeline),'frames':timeline})
    write(args.output_dir/'provenance.json',{'activity':args.activity,'profile':args.profile,
        'human_policy':'actual_qwen3_intention_and_action_no_lora','human_model':str(args.human_model),
        'human_model_class':type(human._model).__name__,'human_thinking_enabled':human.enable_thinking,
        'human_executor':'human_only_continuous_kinematic_attachment','robot_model_metadata':client.get_server_metadata(),
        'robot_system':'visual_coordinator_plus_vla' if coordinator else 'direct_vla_public_dialogue',
        'coordinator_metadata':coordinator.metadata if coordinator else None,
        'private_intent_in_robot_input':False,'background_task_action_router':False,
        'context_step':args.context_step,'steps':args.steps,'init_state_id':args.init_state_id,'seed':args.seed,
        'source_sha256':hashes,'source_files_changed_during_run':[str(p) for p in paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'cuda_visible_devices':chosen,'renderer_device_binding':device})
    finalize_video_verification(args.output_dir,required=True)
    decisions=json.dumps([{'time_s':d['time_s'],'choice':d['choice']} for d in human.decisions],ensure_ascii=False).replace('<','\\u003c')
    public_json=json.dumps(dialogue,ensure_ascii=False).replace('<','\\u003c')
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{activity.label}</title><style>body{{max-width:1100px;margin:auto;padding:24px;background:#edf3f1;color:#193c43;font:17px/1.8 system-ui;overflow-wrap:anywhere}}video{{width:100%}}pre{{white-space:pre-wrap;background:white;padding:18px}}section{{background:white;padding:22px;margin:20px 0}}</style><h1>{activity.label}：在线人策略与真实机器人</h1><section><p>{escape(activity.public_description)}</p><p>人的动作使用连续运动学持物约束；机器人由真实VLA输出原生OSC动作。人模型每2秒更新，机器人每10步重新观察。双方通过实际场景与公开话语交互。人私有需要仅在研究记录中保存，不自动转发机器人。当前是开发运行，尚不能称完整Benchmark。</p><p><a href="summary.json">结果</a> · <a href="provenance.json">模型和执行边界</a> · <a href="episode/human_policy_io.jsonl">人私有输入与原始推理</a> · <a href="episode/model_calls.jsonl">机器人实际收到的输入</a></p></section><video id="sim" controls playsinline preload="metadata" src="episode/demo.mp4" poster="episode/preview.png"></video><pre id="state"></pre><section><h2>实际记录</h2><pre>{escape(json.dumps(result,ensure_ascii=False,indent=2))}</pre><p>原生机器人任务成立不等于完整共同活动成立；意图文本变化需结合实际行动、公开表达和后续响应解释。</p></section><script>const ds={decisions},ms={public_json};const v=document.getElementById('sim'),s=document.getElementById('state');function update(){{let d=ds[0];for(const x of ds)if(x.time_s<=v.currentTime)d=x;const spoken=ms.filter(x=>x.time_s<=v.currentTime).slice(-4);s.textContent='模拟 '+v.currentTime.toFixed(2)+'秒\n人的当次选择（研究视图）：'+JSON.stringify(d.choice,null,2)+'\n已经公开的交流：'+JSON.stringify(spoken,null,2);}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();</script></html>'''
    (args.output_dir/'index.html').write_text(page);print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
