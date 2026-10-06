#!/usr/bin/env python3
"""在原生LIBERO执行中国源π0.5，录制真实场景、双相机与完整原生动作。"""
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

from hrc_pilot.libero_native import native_policy_input, input_audit, physical_record
from hrc_pilot.video_verification import finalize_video_verification


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--suite', default='libero_spatial')
    parser.add_argument('--task-ids', type=int, nargs='+', default=[0, 1, 2])
    parser.add_argument('--init-state-ids', type=int, nargs='+', default=[0])
    parser.add_argument('--seed', type=int, default=30)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--steps', type=int, default=280)
    parser.add_argument('--execution-horizon', type=int, default=10)
    parser.add_argument('--human-mode', choices=['none','observe','qwen','calibration'], default='none')
    parser.add_argument('--human-persona', choices=['cooperative','independent','cautious','assertive'], default='cooperative')
    parser.add_argument('--human-model', type=Path, default=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B'))
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('请使用新的输出目录')
    if args.steps < 1 or args.execution_horizon < 1:
        parser.error('步数与执行块长度必须为正整数')
    free_rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free',
                                        '--format=csv,noheader,nounits'], text=True)
    free = {row.split(',')[0].strip(): int(row.split(',')[1]) for row in free_rows.splitlines()}
    selected = os.environ.get('CUDA_VISIBLE_DEVICES')
    required = 4096
    if args.human_mode == 'qwen':
        required = sum(p.stat().st_size for p in args.human_model.glob('*.safetensors'))//(1024**2)+8192
    if selected not in free or free[selected] < required:
        parser.error(f'原生Sim与所选伙伴预计需要{required}MiB，请指定单張显存足够的GPU')
    print(f'[native-libero] GPU{selected} 空闲{free[selected]}MiB', flush=True)
    pci_rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,pci.bus_id','--format=csv,noheader'],text=True)
    pci={row.split(',')[0].strip():row.split(',')[1].strip().lower()[-12:] for row in pci_rows.splitlines()}
    probe_env=dict(os.environ)
    probe_env.pop('CUDA_VISIBLE_DEVICES',None)
    probe_env['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    mapping=json.loads(subprocess.check_output([sys.executable,str(Path(__file__).with_name('probe_egl_devices.py'))],
                                               env=probe_env,text=True))
    matched=[r for r in mapping if r['pci_bus']==pci[selected]]
    if len(matched)!=1:parser.error('不能唯一对应物理GPU与EGL设备，禁止跨卡渲染')
    os.environ['CUDA_DEVICE_ORDER']='PCI_BUS_ID'
    os.environ['MUJOCO_EGL_DEVICE_ID']=str(matched[0]['egl_ordinal'])
    print(f'[native-libero] EGL{matched[0]["egl_ordinal"]} → 物理GPU{selected} PCI{pci[selected]}',flush=True)
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv
    from openpi_client.websocket_client_policy import WebsocketClientPolicy
    import mujoco
    import torch
    import robosuite
    client = WebsocketClientPolicy('127.0.0.1', args.port)
    metadata = client.get_server_metadata()
    if metadata.get('action_encoding') != 'libero_osc_delta':
        parser.error('需要实际π0.5-LIBERO原生末端增量模型服务')
    suite = benchmark.get_benchmark_dict()[args.suite]()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    code_paths = [Path(__file__), Path('src/hrc_pilot/libero_native.py'), Path('src/hrc_pilot/native_contact_human.py'),
                  Path('src/hrc_pilot/llm_human.py'),Path('src/hrc_pilot/human_contact.py'),
                  Path(__file__).with_name('probe_egl_devices.py')]
    hashes = {str(p): sha256(p.read_bytes()).hexdigest() for p in code_paths}
    episodes, provenance_episodes = [], []
    partner = None
    if args.human_mode == 'qwen':
        from hrc_pilot.native_contact_human import NativeQwenHuman
        from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
        from dataclasses import replace
        partner = NativeQwenHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),
                                 model_path=args.human_model, persona_id=args.human_persona,
                                 decision_interval_steps=20, memory_scope='session')
        partner.prepare()
    for task_id in args.task_ids:
        task = suite.get_task(task_id)
        bddl = Path(suite.get_task_bddl_file_path(task_id))
        initial_path = Path(get_libero_path('init_states')) / task.problem_folder / task.init_states_file
        initial_states = torch.load(initial_path, weights_only=False, map_location='cpu')
        for initial_id in args.init_state_ids:
            directory = args.output_dir / f'task_{task_id:02d}' / f'init_{initial_id:03d}'
            directory.mkdir(parents=True)
            env = OffScreenRenderEnv(bddl_file_name=str(bddl), control_freq=20,
                                     camera_names=['agentview', 'robot0_eye_in_hand', 'frontview'],
                                     camera_heights=[256, 256, 480], camera_widths=[256, 256, 640],
                                     render_gpu_device_id=0)
            trace, policy_io, timeline, calls = [], [], [], []
            action_plan = deque()
            writer = imageio.get_writer(directory / 'demo.mp4', fps=20)
            def frame(obs, *, benchmark_time=None):
                raw = (env.sim.render(width=640,height=480,camera_name='hrc_view')
                       if args.human_mode!='none' else obs['frontview_image'])
                pixels = np.ascontiguousarray(raw[::-1, ::-1])
                writer.append_data(pixels)
                if not timeline:
                    Image.fromarray(pixels).save(directory / 'preview.png')
                timeline.append({'frame': len(timeline), 'video_time_s': len(timeline)/20,
                                 'benchmark_time_s': benchmark_time,
                                 'physics_time_s': float(env.sim.data.time)})
            try:
                env.seed(args.seed)
                env.reset()
                obs = env.set_init_state(initial_states[initial_id])
                for _ in range(10):
                    obs, _, _, _ = env.step([0.] * 6 + [-1.])
                    if args.human_mode=='none':frame(obs)
                actor, regions, messages, contact_witness = None, {}, [], False
                initial_plate, plate_goal, human_dwell = None, None, 0
                if args.human_mode != 'none':
                    from hrc_pilot.native_contact_human import augment_contact_human, NativeContactHuman
                    from hrc_pilot.protocol import Message, Observation
                    from hrc_pilot.continuous import HumanCommand
                    initial_plate = env.sim.data.body_xpos[env.env.obj_body_id['plate_1']].copy()
                    plate_goal = initial_plate + [0,.12,0]
                    regions = {'near_human':tuple(plate_goal)}
                    obs = augment_contact_human(env,plate_goal)
                    actor = NativeContactHuman(env,regions)
                    actor._display(actor.position())
                    env.sim.forward()
                    env.env._update_observables(force=True)
                    obs=env.env._get_observations()
                    messages = [Message('environment','activity_change','餐桌共同准备；安排按当前可见进度调整。'),
                                Message('human','assignment',task.language,None,'robot',None),
                                Message('human','assignment','I want to move plate_1 to the green near_human area while you place the specified bowl on it.',
                                        'plate_1','human','near_human')]
                    if partner is not None:partner.reset(args.seed)
                start_physics = float(env.sim.data.time)
                (directory/'scene.xml').write_text(env.sim.model.get_xml())
                done = False
                for step in range(args.steps):
                    time_s = step / 20
                    record = physical_record(env, obs, time_s=time_s, step=step)
                    if actor is not None:
                        record['human_hand_position'] = actor.position().tolist()
                        record['human_motor_phase'] = actor.phase
                        if partner is not None:
                            public = Observation(objects={k:tuple(v) for k,v in record['objects'].items()},
                                regions=regions,messages=tuple(messages),robot_ee=tuple(record['robot_ee']),
                                human_position=(.25,.60,0),held_by_human=(),completed_skills=(),
                                time_s=time_s,robot_qpos=tuple(record['robot_qpos']),
                                task_description=task.language,human_hand_position=tuple(actor.position()),
                                human_motor_phase=actor.phase,active_robot_action='placing_bowl',action_phase='native_control')
                            decision=partner.step(public)
                            messages.extend(decision.messages)
                            actor.accept(decision.command)
                        elif args.human_mode=='calibration':
                            actor.accept(HumanCommand('push','plate_1','near_human',speed_mps=.15))
                    trace.append(record)
                    frame(obs, benchmark_time=time_s)
                    if not action_plan:
                        instruction=task.language
                        if partner is not None:
                            communication=[m.text for m in messages if m.kind=='policy_message'][-2:]
                            if communication:instruction += '\nHuman: '+'\nHuman: '.join(communication)
                        request = native_policy_input(obs, instruction)
                        stem = f'observation_{step:06d}'
                        Image.fromarray(request['observation/image']).save(directory / f'{stem}.png')
                        Image.fromarray(request['observation/wrist_image']).save(directory / f'{stem}_wrist.png')
                        started = time.perf_counter()
                        chunk = np.asarray(client.infer(request)['actions'], dtype=float)
                        if chunk.ndim != 2 or chunk.shape[1] != 7 or not np.isfinite(chunk).all():
                            raise ValueError('实际模型必须输出有限N×7原生动作')
                        count = min(len(chunk), args.execution_horizon)
                        call = {'model_call': len(calls)+1, 'step': step, 'time_s': time_s,
                                **input_audit(request), 'exterior_artifact': f'{stem}.png',
                                'wrist_artifact': f'{stem}_wrist.png', 'raw_action_chunk': chunk.tolist(),
                                'latency_s': time.perf_counter()-started}
                        calls.append(call)
                        action_plan.extend((index, chunk[index]) for index in range(count))
                    chunk_index, action = action_plan.popleft()
                    policy_io.append({'step': step, 'time_s': time_s, 'model_call': calls[-1]['model_call'],
                                      'executed_chunk_index': chunk_index, 'action': action.tolist(),
                                      'pre_physics_time_s': float(env.sim.data.time)})
                    obs, reward, _, info = env.step(action.tolist())
                    done = bool(env.check_success())
                    if actor is not None:
                        recent=actor.records[-int(round(.05/actor.dt)):]
                        plate_geoms=set(env.env.objects_dict['plate_1'].contact_geoms)
                        contact_witness = contact_witness or any(plate_geoms.intersection(row['contact_geoms']) for row in recent)
                        actual_plate=actor.object_position('plate_1')
                        plate_speed=(np.linalg.norm(np.asarray(recent[-1]['object_position'])-recent[0]['object_position'])/
                                     max(recent[-1]['physics_time_s']-recent[0]['physics_time_s'],actor.dt)
                                     if len(recent)>1 and recent[0]['object_position'] is not None else np.inf)
                        human_geometry=bool(np.linalg.norm(actual_plate[:2]-plate_goal[:2])<.025
                                            and abs(actual_plate[2]-initial_plate[2])<.025 and plate_speed<.08)
                        human_dwell=human_dwell+1 if human_geometry and contact_witness else 0
                        human_success=human_dwell>=4
                        if args.human_mode=='qwen':done=done and human_success
                        elif args.human_mode=='calibration':done=human_success
                    policy_io[-1].update(post_physics_time_s=float(env.sim.data.time),
                                         actuator_ctrl=env.sim.data.ctrl.tolist())
                    if not np.isclose(env.sim.data.time-start_physics, (step+1)/20, atol=1e-7):
                        raise RuntimeError('原生物理时间没有按20Hz控制推进')
                    if done:
                        break
                terminal = physical_record(env, obs, time_s=(step+1)/20, step=step+1)
                trace.append(terminal)
                frame(obs, benchmark_time=terminal['time_s'])
                for filename, rows in [('trace.jsonl', trace), ('policy_io.jsonl', policy_io), ('model_calls.jsonl', calls)]:
                    (directory / filename).write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows))
                result = {'scenario': task.name, 'instruction': task.language, 'task_id': task_id,
                          'init_state_id': initial_id, 'seed': args.seed, 'task_success': done,
                          'completion_time_s': terminal['time_s'], 'model_calls': len(calls),
                          'native_actions': len(policy_io), 'backend': 'LIBERO_MuJoCo_native',
                          'interpretation': '原生基础操作参照，不含人类，不是HRC/cobalance成绩。'}
                if actor is not None:
                    motion_peak=max(float(np.linalg.norm(row['actual_velocity'])) for row in actor.records)
                    object_speeds=[np.linalg.norm(np.asarray(second['object_position'])-first['object_position'])/
                                   (second['physics_time_s']-first['physics_time_s'])
                                   for first,second in zip(actor.records,actor.records[1:])
                                   if first['object_id']==second['object_id'] and first['object_position'] is not None
                                   and second['object_position'] is not None]
                    object_speed_peak=max(object_speeds,default=0.)
                    result.update(human_mode=args.human_mode,human_contact_witness=contact_witness,
                                  human_goal_success=human_dwell>=4, robot_goal_success=bool(env.check_success()),
                                  human_fingertip_peak_speed_m_s=motion_peak,
                                  human_object_peak_speed_m_s=float(object_speed_peak),
                                  human_motion_check_passed=bool(motion_peak<=.65 and object_speed_peak<=1.5),
                                  final_plate_position=actor.object_position('plate_1').tolist(),
                                  public_plate_target=plate_goal.tolist(),
                                  interpretation='真实模型与可选生成式伙伴在同一世界中的移动接收盘任务；人体显示是运动学代理，指尖是力驱动碰撞体，不证明真人效度。')
                    (directory/'human_control.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in actor.records))
                    write_json(directory/'public_task.json',{'robot':task.language,'human':'Move plate_1 to near_human',
                                                           'initial_plate':initial_plate.tolist(),'near_human':plate_goal.tolist()})
                    if partner is not None:
                        audit=partner.audit_state()
                        for name,key in [('human_policy_io.jsonl','policy_io'),('human_memory.jsonl','memory'),
                                         ('human_memory_retrievals.jsonl','memory_retrievals')]:
                            (directory/name).write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in audit[key]))
                        result['human_decisions']=len(audit['policy_io'])
                write_json(directory/'metrics.json', result)
                write_json(directory/'video_timeline.json', {'fps':20,'frame_count':len(timeline),'frames':timeline})
                episodes.append(result)
                provenance_episodes.append({'task_id':task_id,'init_state_id':initial_id,
                                            'bddl_sha256':sha256(bddl.read_bytes()).hexdigest(),
                                            'init_file_sha256':sha256(initial_path.read_bytes()).hexdigest()})
                print(f'[native-libero] task{task_id} init{initial_id}: 成功{done}，{len(calls)}次真实调用', flush=True)
            finally:
                writer.close()
                env.close()
    write_json(args.output_dir/'summary.json', {'episodes':episodes,'successes':sum(r['task_success'] for r in episodes),
                                               'episode_count':len(episodes)})
    write_json(args.output_dir/'provenance.json', {'backend':'LIBERO_MuJoCo_native','trained_model':True,
        'model_server_metadata':metadata,'suite':args.suite,'seed':args.seed,'control_hz':20,
        'execution_horizon':args.execution_horizon,'max_steps':args.steps,'settle_steps':10,
        'mujoco_version':mujoco.__version__,'robosuite_version':robosuite.__version__,
        'libero_commit':subprocess.check_output(['git','-C',str(Path(get_libero_path('benchmark_root')).parents[1]),'rev-parse','HEAD'],text=True).strip(),
        'cuda_visible_devices':selected,'source_sha256':hashes,
        'renderer_device_binding':matched[0],
        'human_mode':args.human_mode,'human_persona':args.human_persona if partner is not None else None,
        'human_model':str(args.human_model) if partner is not None else None,
        'human_physics':'force_driven_xyz_fingertip' if args.human_mode!='none' else None,
        'human_body_visualization':'noncolliding_kinematic_capsules' if args.human_mode!='none' else None,
        'human_goal_definition':'plate center within 25mm XY of visible marker, near original support height, speed under 0.08m/s for 0.2s, with physical fingertip contact witness',
        'source_files_changed_during_run':[str(p) for p in code_paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'episodes':provenance_episodes,'object_pose_writes_during_control':0,'robot_ik_adapter':False,
        'purpose':'用匹配的原生场景、相机、状态和操作空间控制验证现成模型的基础操作能力。',
        'interpretation':'原生参照不证明模型已具备动态人类协作能力；不能与不同域的Genesis失败作严格配对因果比较。'})
    finalize_video_verification(args.output_dir, required=True)
    panels=[]
    for result in episodes:
        location=f'task_{result["task_id"]:02d}/init_{result["init_state_id"]:03d}'
        panels.append(f'<article><h2>{escape(result["instruction"])}</h2><p>原生初始状态{result["init_state_id"]}；{"完成" if result["task_success"] else "未完成"}；模拟{result["completion_time_s"]:.2f}秒，真实推理{result["model_calls"]}次。</p><video controls preload="metadata" poster="{location}/preview.png" src="{location}/demo.mp4"></video></article>')
    human_note = ('测试没有人类伙伴，不能解释为协作成绩。' if args.human_mode=='none' else
                  '加入力驱动的碰撞指尖和不参与碰撞的显示人体。observe用于场景接入检查，calibration的推盘命令来自数据教师，qwen才使用真实Qwen3-14B决定推进、观察和让行。机器人一直执行真实π0.5；人体显示仍是简化运动学代理，不能声称真人或完整人体动力学。')
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原生仿真策略与移动接收盘</title><style>body{{margin:auto;max-width:1080px;padding:24px;background:#f1f5f4;font:17px/1.8 system-ui;color:#193540;overflow-wrap:anywhere}}article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}video{{width:100%;max-height:600px;background:#142430}}h1{{font-size:30px}}h2{{font-size:22px}}</style><h1>真实π0.5模型与可变化的接收盘</h1><p>此前Genesis中的机器人未建立可靠抓放。这里保持已下载模型权重，使用配套原生场景、两路相机、末端状态及OSC控制，区分基础操作问题与接入域差异。{human_note}</p><p>20Hz物理控制；每次模型输出最多执行{args.execution_horizon}步后重新观察。视频直接记录Sim场景；机器人没有教师接管，物体没有吸附。伙伴条件：{args.human_mode}。结果：{sum(r['task_success'] for r in episodes)}/{len(episodes)}。当前样本是系统实测，不作为完整HRC或全套LIBERO排名。</p><p><a href="summary.json">原始结果</a> · <a href="provenance.json">设置与来源</a> · <a href="video_verification.json">视频核验</a></p>{''.join(panels)}</html>'''
    (args.output_dir/'index.html').write_text(page)
    print(args.output_dir/'index.html', flush=True)


if __name__ == '__main__':
    main()
