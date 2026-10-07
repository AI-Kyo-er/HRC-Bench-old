"""将模型选定空间动作、真实运动与当前目标结果分开报告。"""
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
CASES={'bowl_on_stove':'碗放炉面与个人整理','food_into_bowl':'奶酪入碗与移动接收物整理','food_into_bowl_direct':'直接π0.5：奶酪入碗与个人整理'}
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()


def main():
    panels=[];table=[];data={};facts=[]
    for key,label in CASES.items():
        run=ROOT/'results/continuous_v2/spatial_coordination_20261007'/key;ep=next(run.glob('task_*/init_000'))
        m=read(run/'summary.json')['episodes'][0];provenance=read(run/'provenance.json')
        assert not provenance['source_files_changed_during_run']
        coordinated=(ep/'robot_planner_io.jsonl').exists()
        for name in ['video_verification','model_execution_verification','personal_verification','human_feedback_verification','relative_geometry_verification']+(['coordination_verification'] if coordinated else []):
            assert read(run/(name+'.json'))['status']=='verified'
        continuous=read(run/'continual_activity_verification.json')['episodes'][0]
        contact=read(run/'hand_robot_contact_verification.json')['episodes'][0]
        spatial=read(run/'spatial_motion_verification.json')['episodes'][0] if coordinated else {'model_selected_spatial_moves':0,'events':[]}
        hand=read(run/'hand_verification.json')['episodes']
        qualifies=read(run/'model_execution_verification.json')['motion_eligible_episode_count']==1 and read(run/'avatar_verification.json')['status']=='verified' and all(r['motion_qualified'] for r in hand)
        human=rows(ep/'human_policy_io.jsonl');plans=rows(ep/'human_planner_io.jsonl');robot=rows(ep/'robot_planner_io.jsonl') if coordinated else [];calls=rows(ep/'model_calls.jsonl')
        sources=Counter(c['action_source'] for c in calls);assert sum(sources.values())==m['model_calls']
        buttons=''.join(f'<button data-video="{key}" data-time="{e["start_s"]}">模型选定位移 · {e["start_s"]:.2f}秒</button>' for e in spatial['events'][:6])
        moves=''.join(f'<tr><td>{e["start_s"]:.2f}–{e["end_s"]:.2f}s</td><td>{escape(str(e["model_requested_delta_xyz_m"]))}</td><td>{e["actual_eef_displacement_m"]*1000:.1f}mm</td><td>{e["remaining_target_distance_m"]*1000:.1f}mm</td><td>{e["human_robot_contact_time_during_move_s"]:.2f}s</td></tr>' for e in spatial['events'])
        targets=''.join(f'<tr><td>{escape(r["object_id"])}</td><td>{escape(r["destination"])}</td><td>{r["first_stable_relation_s"] if r["first_stable_relation_s"] is not None else "未出现"}</td><td>{"满足" if r["terminal_relation_satisfied"] else "未满足"}</td></tr>' for r in m['personal_evidence']['target_intervals'])
        table.append(f'<tr><td>{label}</td><td>{m["actual_vla_model_calls"]}／{m["hold_primitive_calls"]}／{m["cartesian_primitive_calls"]}</td><td>{len(robot)}</td><td>{spatial["model_selected_spatial_moves"]}</td><td>{continuous["semantic_target_set_changes"]}</td><td>{continuous["joint_released_goal_time_s"]:.2f}s</td><td>{contact["hand_robot_contact_record_time_s"]:.2f}s</td><td>{"通过" if qualifies else "诊断"}</td></tr>')
        panels.append(f'''<section><h2>{label}</h2><p>{'机器人处理碗的炉面关系，人可自主安排盘／奶酪，检验共享台面的空间协调。' if key=='bowl_on_stove' else '机器人处理奶酪与接收碗关系，人偏好整理碗／酒瓶；接收物可随人的自主行为移动，不强制触发干预。'}人10次周期意图反思，本次实际反思{len(plans)}次、动作选择{len(human)}次；机器人视觉协调{len(robot)}次。</p><video id="{key}" controls playsinline preload="metadata" poster="{link(ep/'preview.png')}" src="{link(ep/'demo.mp4')}"></video><div>{buttons}</div><pre id="state-{key}"></pre><p class="notice">{'运动与显示资格通过；这不等于任务完成。' if qualifies else '存在运动／显示阈值未通过，本条保留为诊断，不纳入合格Benchmark成绩。'}机器人期末目标{'满足' if m['robot_goal_success'] else '未满足'}；人当前目标{'满足' if m['human_goal_success'] else '未满足'}，{'可评分' if m['human_goal_evaluable'] else '不可评分，空目标不能算成功'}。</p><h3>模型位移选择与实际运动</h3><div class="scroll"><table><tr><th>时间区间</th><th>模型给定位移（米）</th><th>实际末端位移</th><th>剩余目标距离</th><th>同期手／机器人接触</th></tr>{moves or '<tr><td colspan="5">模型没有选择move_ee</td></tr>'}</table></div><p>位移不是让行成功标签。这里分别记录模型目标、实际运动与几何接触；后续任务是否推进仍看下面的实际关系。参考速度界限不替代实际速度测量。</p><h3>人的自主目标与实际关系</h3><div class="scroll"><table><tr><th>物品</th><th>选定关系</th><th>首次释放稳定满足（秒）</th><th>期末</th></tr>{targets}</table></div><p><a href="{link(run/'summary.json')}">原始结果</a> · <a href="{link(run/'spatial_motion_verification.json')}">实际位移与接触区间</a> · <a href="{link(ep/'robot_planner_io.jsonl')}">原始视觉模型选择</a> · <a href="{link(ep/'human_planner_io.jsonl')}">原始人意图</a> · <a href="{link(ep/'human_policy_io.jsonl')}">原始人动作</a> · <a href="{link(run/'coordination_verification.json')}">公开输入与控制来源核验</a> · <a href="{link(run/'video_verification.json')}">视频核验</a></p></section>''')
        if not coordinated:
            panels[-1]=panels[-1].replace(f'<a href="{link(run/"spatial_motion_verification.json")}">实际位移与接触区间</a> · ','').replace(f'<a href="{link(ep/"robot_planner_io.jsonl")}">原始视觉模型选择</a> · ','').replace(f'<a href="{link(run/"coordination_verification.json")}">公开输入与控制来源核验</a> · ','')
        data[key]={'frames':read(ep/'video_timeline.json')['frames'],
            'human':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'targets':h['personal_goal_state']['personal_targets'],
                'received_execution':json.loads(h['public_input'].split('\n',1)[1])['your_measured_execution']} for h in human],
            'robot':[{'time_s':r['time_s'],'decision':r['decision'],'own_measured_execution':r['public_input']['self_execution']} for r in robot]}
        facts.append({'scene':key,'motion_qualified':qualifies,'sources':dict(sources),'robot_visual_calls':len(robot),
            'human_inferences':len(human)+len(plans),'model_selected_moves':spatial['model_selected_spatial_moves'],
            'robot_goal_success':m['robot_goal_success'],'human_goal_success':m['human_goal_success'],
            'joint_goal_time_s':continuous['joint_released_goal_time_s'],'hand_robot_contact_time_s':contact['hand_robot_contact_record_time_s']})
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>可执行空间协调与动态接收物</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{margin:22px 0;padding:24px;background:white;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px)}}h2{{font-size:24px}}video{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef5f2;padding:16px}}.notice{{background:#fff1d8;padding:16px;border-radius:8px}}.scroll{{overflow-x:auto}}table{{width:100%;min-width:780px;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}button{{font:inherit;cursor:pointer;padding:7px 12px;margin:8px}}@media(max-width:600px){{main{{padding:12px}}header,section{{padding:18px 14px}}}}</style><main><header><h1>能行动的空间协调与动态接收物</h1><p>三段完整60秒、三机位运行视频。视觉模型现在可以选定实际空间位移；是否推进共同活动，用实际动作与目标关系判断。</p></header><section><h2>本轮要解决的限制</h2><p>此前视觉协调器只能继续VLA或原地保持，在等待人的同时可能继续挡着人。现在增加move_ee：由Qwen3-VL自己根据真实相机、本体、自身接触与公开对话给出末端位移，程序仅校验并执行。没有“检测到接触就自动让行”的规则，也没有评分驱动的任务路由。</p><p>这是一个视觉模型＋π0.5＋运动原语的混合机器人策略。位移原语和保持均单独标记，不是π0.5学习动作；不能把混合策略结果解释为π0.5自身HRC能力或公平模型排名。</p></section><section><h2>任务与设置</h2><p>两种原生LIBERO／MuJoCo场景、三条实际运行，init0／seed0、20Hz、60秒，一次世界和人策略初始化。机器人视觉模型每2秒重估，execute时由真实π0.5输出7维原生动作；move_ee目标完全由视觉模型给定，最长0.2米，参考速度最多0.05m/s，每0.5秒动作块重新读取实际末端位置，保持方向与夹爪命令。不会自动避碰或保证整个手臂清离。</p><p>人的Qwen3-14B策略保持原配置：自主私人意图每6秒反思、每2秒动作选择，新消息可触发推理；没有定时目标或人动作清单。人读理想几何，身体为骨骼显示，双指手实际受力。人私人目标／偏好和评分不进入机器人输入。视频按模拟时钟播放，推理墙钟较慢。</p><p><a href="PLAN.md">运行协议与边界</a> · <a href="README.md">实测说明</a> · <a href="../progress_20261007/index.html">此前总体进展</a></p></section><section><h2>实际结果</h2><div class="scroll"><table><tr><th>活动</th><th>VLA／保持／位移块</th><th>视觉推理</th><th>位移选择</th><th>人目标变化</th><th>共同目标满足时间</th><th>手／机器人接触</th><th>运动资格</th></tr>{''.join(table)}</table></div><p>各类动作分开计数。视觉选择、公开回应、接触减少与任务满足是不同证据；当前小样本没有严格配对，不进行改善因果归因。</p></section>{''.join(panels)}<section><h2>结论边界</h2><p>系统已支持模型驱动的空间协调与可移动接收物场景；是否形成有效重新组织，要看上面的实际运动和双方当前目标，不能只看出现move_ee或更多对话。人策略可靠操作、带负载容器、完整人体动力学、更多任务／模型／初始化及cobalance构念效度仍未完成。完整成熟Benchmark目标继续保持未完成。</p></section></main><script>const runs={payload};for(const [key,r]of Object.entries(runs)){{const v=document.getElementById(key),s=document.getElementById('state-'+key);function update(){{let f=r.frames[0];for(const a of r.frames)if(a.video_time_s<=v.currentTime)f=a;const t=f.benchmark_time_s||0;let h=r.human[0],b=r.robot[0]||{time_s:0,decision:{mode:"原生π0.5持续操作",instruction:"公开任务与公开人消息",reason:"直接学习VLA，没有视觉协调层",message:""},own_measured_execution:{own_contact_report:"本条件无视觉协调层输入"}};for(const a of r.human)if(a.time_s<=t)h=a;for(const a of r.robot)if(a.time_s<=t)b=a;s.textContent=`模拟 ${{t.toFixed(2)}}秒\n机器人最新视觉选择（${{b.time_s.toFixed(2)}}秒）：${{b.decision.mode}} ${{JSON.stringify(b.decision.delta_xyz_m||b.decision.instruction)}}\n理由：${{b.decision.reason}}\n公开回应：${{b.decision.message}}\n该次输入的自身接触：${{JSON.stringify(b.own_measured_execution.own_contact_report)}}\n人的最新选择（${{h.time_s.toFixed(2)}}秒）：${{h.decision.intent}} ${{h.decision.object_id||''}} → ${{h.decision.destination||''}}\n私人目标：${{JSON.stringify(h.targets)}}\n该次输入的实际在手物体：${{h.received_execution.object_measured_in_hand||'无'}}\n人理由：${{h.decision.reason}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}document.querySelectorAll('button').forEach(b=>b.onclick=()=>document.getElementById(b.dataset.video).currentTime=Number(b.dataset.time));</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'facts.json').write_text(json.dumps({'research_goal_achieved':False,'episodes':facts},ensure_ascii=False,indent=2))
    print(json.dumps(facts,ensure_ascii=False))

if __name__=='__main__':main()
