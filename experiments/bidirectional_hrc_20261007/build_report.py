"""公开双向协调模型的原始选择、对话和真实物理执行。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2/bidirectional_hrc'
FAMILIES={'prepare_receptacle':'先准备接收盘','shared_workspace':'共享空间中的邻近操作','clearance_return':'退离、返回与准备盘子'}


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
def href(path):return '../../'+path.relative_to(ROOT).as_posix()


def main():
    panels=[];table=[];audits={};evidence={};sources=[]
    for family,label in FAMILIES.items():
        root=RESULTS/family
        names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json',
               'avatar_verification.json','human_feedback_verification.json','placement_verification.json','coordination_verification.json']
        data={name:read(root/name) for name in names};sources.extend(root/name for name in names)
        assert data['video_verification.json']['status']=='verified'
        assert data['coordination_verification.json']['status']=='verified'
        assert not data['provenance.json']['source_files_changed_during_run']
        metric=data['summary.json']['episodes'][0];episode=root/'task_02/init_000'
        robot=rows(episode/'robot_planner_io.jsonl');human=rows(episode/'human_policy_io.jsonl')
        modes=Counter(r['decision']['mode'] for r in robot)
        intents=Counter(h['parsed_decision']['intent'] for h in human)
        audit=data['coordination_verification.json']['episodes'][0]
        valid=data['model_execution_verification.json']['motion_eligible_episode_count']==1 and data['avatar_verification.json']['qualified_count']==1
        table.append(f'<tr><td>{label}</td><td>{int(metric["robot_goal_success"])}</td><td>{int(metric["human_goal_success"])}</td><td>{int(metric["task_success"])}</td><td>{metric["actual_vla_model_calls"]}</td><td>{metric["hold_primitive_calls"]}</td></tr>')
        audits[family]={'robot':[{k:r[k] for k in ['time_s','decision','parse_error']} for r in robot],
                        'human':[{'time_s':h['time_s'],'decision':h['parsed_decision']} for h in human]}
        panels.append(f'''<article><h2>{label}</h2><p>{"共同完成" if metric['task_success'] else "未共同完成"}，模拟{metric['completion_time_s']:.1f}秒。视觉协调模型推理{metric['robot_planner_model_calls']}次，π0.5真实推理{metric['actual_vla_model_calls']}次，保持原语{metric['hold_primitive_calls']}个控制块。动作/显示资格{"通过" if valid else "未通过，仅诊断"}。</p><video controls preload="metadata" poster="{href(episode/'preview.png')}" src="{href(episode/'demo.mp4')}" data-audit="{family}"></video><div class="audit" id="audit-{family}"></div><p>机器人模式：{escape('、'.join(f'{k} {v}次' for k,v in modes.items()))}；人的意图：{escape('、'.join(f'{k} {v}次' for k,v in intents.items()))}。机器人发出{audit['robot_messages']}条消息，{audit['human_model_inputs_containing_robot_messages']}次人模型输入实际包含机器人消息。协调输出解析失败{audit['planner_parse_errors']}次。</p><p><a href="{href(episode/'metrics.json')}">原始结果</a> · <a href="{href(episode/'robot_planner_io.jsonl')}">视觉协调模型原始输入输出</a> · <a href="{href(episode/'public_dialogue.jsonl')}">完整公开对话</a> · <a href="{href(root/'coordination_verification.json')}">双向信息与控制来源核查</a></p></article>''')
        evidence[family]=data
        sources.extend(episode/name for name in ['robot_planner_io.jsonl','human_policy_io.jsonl','public_dialogue.jsonl'])
    js=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>双向协调与实际执行</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:650px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style><main><header><h1>双方都能说话和调整当前动作</h1><p>新增Qwen3-VL视觉机器人协调层，读取实际相机、自身状态和公开对话。它自主决定调用π0.5执行运动，或保持姿态，并向Qwen人类伙伴发消息。三类任务完整录制真实Sim视频。</p></header>
<section><h2>目的与实际设置</h2><p>此前机器人只接收人的话，不能主动回应。现在机器人可提出等待和时序安排，人的后续输入确实接收到这些消息；双方仍依据自己的实际观察决定动作。视觉模型的文字计划不会由程序自动执行，评分器不选择策略。</p><p>组合是Qwen3-VL-8B协调器＋真实π0.5执行器；人仍为Qwen3-14B、合作倾向、episode记忆。task2/init0/seed0，20Hz，最多30秒。协调器每1秒看初始/当前外部相机及当前腕部相机，还有机械臂自身8维状态和公开任务对话；不读取物体理想坐标或私有任务成绩。人使用理想坐标与执行反馈，另获得实际绿色区域形状/半径，帮助区分面积区域与精确点。</p><p>execute来自π0.5原始运动输出；hold是模型选择的零位移、维持开闭状态的低层原语。无效协调输出的保护保持单独标记，不能叫作模型自主等待。机器人动作仍通过真实物理控制，物体不吸附、不改写控制期坐标；人体仍是非碰撞骨骼显示与受力指尖代理。</p><p class="notice">这是新增层级算法的系统实测，不是原始π0.5能力成绩。相比上一批，算法组合、公开区域描述和30秒预算均有改变，不作因果提升比较。双向消息接通不等于协商理解或cobalance能力已验证。</p></section>
<section><h2>结果按执行证据解释</h2><div class="table-wrap"><table><tr><th>任务</th><th>机器人完成</th><th>人完成</th><th>共同完成</th><th>VLA实际推理</th><th>保持原语块</th></tr>{''.join(table)}</table></div><p>首条任务中，机器人在初始空夹爪时声称已经拿着碗，随后持续等待；人的确认消息也与盘子实际位置不一致。这些是模型原始输出，而非已执行的事实。视频与原始日志并列呈现，不把说“已完成”当作物理贡献。</p></section>
{''.join(panels)}<section><h2>仍需推进</h2><p>新增了真实双向信息流与视觉协调器，但原始分工仍固定，尚未实现完整角色协商、开放目标和持续世界。人的真实抓持/身体碰撞、更多技能和场景、多人格效度仍缺验证。当前失败提示需要把模型自己的实际执行与生成的计划/记忆分开，并验证感知可靠性；不能通过评分器替代这些能力。</p><p><a href="../two_model_hrc_20261007/index.html">上一批两模型三层实测</a> · <a href="evidence.json">结果与来源</a></p></section></main>
<script>const audits={js};document.querySelectorAll('video[data-audit]').forEach(video=>{{const target=document.getElementById('audit-'+video.dataset.audit);function update(){{const data=audits[video.dataset.audit];let robot=data.robot[0],human=data.human[0];for(const r of data.robot)if(r.time_s<=video.currentTime)robot=r;for(const h of data.human)if(h.time_s<=video.currentTime)human=h;target.textContent=`机器人 ${{robot.time_s.toFixed(2)}}s · ${{robot.decision.mode}}\n说：${{robot.decision.message}}\n理由：${{robot.decision.reason}}\n运动指令：${{robot.decision.instruction||'保持原语'}}\n人 ${{human.time_s.toFixed(2)}}s · ${{human.decision.intent}}\n说：${{human.decision.message}}\n理由：${{human.decision.reason}}`;}}video.addEventListener('timeupdate',update);video.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'runs':evidence,
        'source_sha256':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sources}},ensure_ascii=False,indent=2))
    print(HERE/'index.html')


if __name__=='__main__':main()
