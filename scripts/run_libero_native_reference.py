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
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('请使用新的输出目录')
    if args.steps < 1 or args.execution_horizon < 1:
        parser.error('步数与执行块长度必须为正整数')
    free_rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free',
                                        '--format=csv,noheader,nounits'], text=True)
    free = {row.split(',')[0].strip(): int(row.split(',')[1]) for row in free_rows.splitlines()}
    selected = os.environ.get('CUDA_VISIBLE_DEVICES')
    if selected not in free or free[selected] < 4096:
        parser.error('原生Sim预计需要4GiB，请指定单张显存足够的GPU')
    print(f'[native-libero] GPU{selected} 空闲{free[selected]}MiB', flush=True)
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
    args.output_dir.mkdir(parents=True)
    code_paths = [Path(__file__), Path('src/hrc_pilot/libero_native.py')]
    hashes = {str(p): sha256(p.read_bytes()).hexdigest() for p in code_paths}
    episodes, provenance_episodes = [], []
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
                pixels = np.ascontiguousarray(obs['frontview_image'][::-1, ::-1])
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
                    frame(obs)
                start_physics = float(env.sim.data.time)
                done = False
                for step in range(args.steps):
                    time_s = step / 20
                    record = physical_record(env, obs, time_s=time_s, step=step)
                    trace.append(record)
                    frame(obs, benchmark_time=time_s)
                    if not action_plan:
                        request = native_policy_input(obs, task.language)
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
        'source_files_changed_during_run':[str(p) for p in code_paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'episodes':provenance_episodes,'object_pose_writes_during_control':0,'robot_ik_adapter':False,
        'purpose':'用匹配的原生场景、相机、状态和操作空间控制验证现成模型的基础操作能力。',
        'interpretation':'原生参照不证明模型已具备动态人类协作能力；不能与不同域的Genesis失败作严格配对因果比较。'})
    finalize_video_verification(args.output_dir, required=True)
    panels=[]
    for result in episodes:
        location=f'task_{result["task_id"]:02d}/init_{result["init_state_id"]:03d}'
        panels.append(f'<article><h2>{escape(result["instruction"])}</h2><p>原生初始状态{result["init_state_id"]}；{"完成" if result["task_success"] else "未完成"}；模拟{result["completion_time_s"]:.2f}秒，真实推理{result["model_calls"]}次。</p><video controls preload="metadata" poster="{location}/preview.png" src="{location}/demo.mp4"></video></article>')
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原生仿真策略操作参照</title><style>body{{margin:auto;max-width:1080px;padding:24px;background:#f1f5f4;font:17px/1.8 system-ui;color:#193540;overflow-wrap:anywhere}}article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}video{{width:100%;max-height:600px;background:#142430}}h1{{font-size:30px}}h2{{font-size:22px}}</style><h1>真实π0.5模型在原生LIBERO中能否操作？</h1><p>此前Genesis中的机器人未建立可靠抓放。这里保持已下载模型权重，使用配套原生场景、两路相机、末端状态及OSC控制，区分基础操作问题与接入域差异。测试没有人类伙伴，不能解释为协作成绩。</p><p>20Hz物理控制；每次模型输出最多执行{args.execution_horizon}步后重新观察。视频直接记录Sim场景，所有物体通过物理接触运动，没有教师接管或吸附。结果：{sum(r['task_success'] for r in episodes)}/{len(episodes)}。当前样本只作操作参照，不作为全套LIBERO排名。</p><p><a href="summary.json">原始结果</a> · <a href="provenance.json">设置与来源</a> · <a href="video_verification.json">视频核验</a></p>{''.join(panels)}</html>'''
    (args.output_dir/'index.html').write_text(page)
    print(args.output_dir/'index.html', flush=True)


if __name__ == '__main__':
    main()
