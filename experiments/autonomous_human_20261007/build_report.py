"""真实自选意图与两个学习机器人的完整视频报告，区分首次达成和持续维持。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2/autonomous_human'
MODELS={'pi05':'π0.5','openvla':'OpenVLA'}
CONTEXTS={'snack_host':'自己安排点心桌','workspace_owner':'维护自己的工作空间'}


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def href(p):return '../../'+p.relative_to(ROOT).as_posix()
def time(v):return '未发生' if v is None else f'{v:.2f}s'


def main():
    panels=[];table=[];audits={};evidence={};hashes={};findings=[]
    for model,model_label in MODELS.items():
        for context,label in CONTEXTS.items():
            root=RESULTS/model/context;episode=root/'task_02/init_000';key=model+'_'+context
            names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json',
                   'avatar_verification.json','human_feedback_verification.json','placement_verification.json','personal_verification.json']
            names+=['prompt_token_verification.json'] if model=='pi05' else ['preprocessing_verification.json']
            data={n:read(root/n) for n in names}
            for name,value in data.items():
                if name=='placement_verification.json':assert value['status']=='audited'
                elif name=='prompt_token_verification.json':assert value['status'] in {'verified_no_truncation','truncation_detected'}
                elif name not in {'summary.json','provenance.json','avatar_verification.json'}:assert value['status']=='verified'
            assert not data['provenance.json']['source_files_changed_during_run']
            metric=data['summary.json']['episodes'][0];personal=read(episode/'personal_evidence.json')
            human=rows(episode/'human_policy_io.jsonl');placement=rows(episode/'placement_evidence.jsonl')
            trace=rows(episode/'trace.jsonl');dialogue=rows(episode/'public_dialogue.jsonl')
            first_robot=next((p['time_s'] for p in placement if p['released_stable_placement']),None)
            robot_time=sum(.05 for p in placement if p['released_stable_placement'])
            valid=data['model_execution_verification.json']['motion_eligible_episode_count']==1 and data['avatar_verification.json']['qualified_count']==1
            modes=Counter(h['parsed_decision']['intent'] for h in human)
            human_status=('满足' if personal['human_current_observable_goals_satisfied'] else '未满足') if personal['human_current_observable_goals_evaluable'] else '无可测目标'
            table.append(f'<tr><td>{model_label} · {label}{"（仅诊断）" if not valid else ""}</td><td>{personal["observable_target_set_changes"]}</td><td>{personal["new_target_intervals_with_stable_relation"]}</td><td>{human_status}</td><td>{time(first_robot)}</td><td>{int(metric["robot_goal_success"])}</td></tr>')
            audits[key]={'human':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'personal':h['personal_goal_state'],
                                 'proposals':h['negotiation_proposal_messages']} for h in human],
                         'trace':[{k:r[k] for k in ['time_s','objects','human_position','human_hand_position']} for r in trace],
                         'regions':read(episode/'personal_context.json')['regions']}
            target_table=''.join(f'<tr><td>{g["start_s"]:.0f}–{g["end_s"]:.0f}s</td><td>{escape(g["object_id"])} → {escape(g["destination"])}</td><td>{"已在区域" if g["already_in_region_when_chosen"] else "尚未在区域"}</td><td>{time(g["first_stable_relation_s"])}</td><td>{"满足" if g["terminal_relation_satisfied"] else "未满足"}</td></tr>' for g in personal['target_intervals'])
            proposal_audit=data['personal_verification.json']['episodes'][0]
            interaction=metric['interaction_metrics']
            panels.append(f'''<article><h2>{model_label} · {label}</h2><p>实际动作模型调用{metric['actual_vla_model_calls']}次，人模型决定{len(human)}次，原生控制{metric['native_actions']}步；运动/显示资格{'通过' if valid else '未通过，仅诊断'}。期末人的当前可观察目标{human_status}，机器人放置{'完成' if metric['robot_goal_success'] else '未完成'}。</p><video controls preload="metadata" poster="{href(episode/'preview.png')}" src="{href(episode/'demo.mp4')}" data-run="{key}"></video><div class="audit" id="audit-{key}"></div><div class="scroll"><table><tr><th>模型自选区间</th><th>对象与区域</th><th>选择时状态</th><th>首个稳定关系</th><th>区间末状态</th></tr>{target_table or '<tr><td colspan="5">没有可测物体目标；主观意图不按物体成功判定。</td></tr>'}</table></div><p>人动作：{escape('、'.join(f'{k} {v}次' for k,v in modes.items()))}。公开协商提案{personal['public_negotiation_proposals']}条，{proposal_audit['robot_calls_containing_public_proposals']}次机器人请求实际包含提案。目标参数校验异常{personal['target_validation_errors']}次，完整JSON解析异常{sum(h['parse_error'] is not None for h in human)}次。</p><p>实际同时运动{interaction['simultaneous_motion_time_s']:.2f}秒，双方都静止{interaction['both_stationary_time_s']:.2f}秒。运动时长只描述执行，不证明协作理解或人体安全。</p><p>机器人首次有效放置：{time(first_robot)}；累计满足释放稳定关系{robot_time:.2f}秒，期末{'保持' if metric['robot_goal_success'] else '未保持'}。不因一度成功自动结束或由评分器保持动作；这与原始单任务模型的终止协议不同，不能直接作官方排名。</p><p><a href="{href(episode/'human_policy_io.jsonl')}">人的原始输入输出</a> · <a href="{href(episode/'personal_evidence.json')}">自选目标物理证据</a> · <a href="{href(episode/'public_dialogue.jsonl')}">完整公开话语</a> · <a href="{href(root/'personal_verification.json')}">自选与公开边界核查</a></p></article>''')
            if not valid:
                panels[-1]=panels[-1].replace('<video controls',f'<p class="notice">仅诊断：人手峰值速度{data["model_execution_verification.json"]["episodes"][0]["human_peak_speed_m_s"]:.3f}m/s，显示接触点最大误差{data["avatar_verification.json"]["episodes"][0]["max_alignment_error_m"]*1000:.1f}mm；超过0.65m/s与25mm门槛。这条的自主变化和物理关系是原始观测，不纳入合格HRC成绩或训练集。</p><video controls')
            first=human[0]['personal_goal_state']
            findings.append(f'<li>{model_label} · {label}：初始长期意图“{escape(first["long_term_intention"])}”；自选目标集合实际变化{personal["observable_target_set_changes"]}次，新关系稳定达成{personal["new_target_intervals_with_stable_relation"]}个区间；机器人首次有效放置{time(first_robot)}。</li>')
            evidence[key]={**data,'personal_evidence':personal,'robot_first_released_stable_s':first_robot,'robot_stable_relation_total_s':robot_time}
            for path in [*(root/n for n in names),*(episode/n for n in ['personal_context.json','personal_evidence.json','human_policy_io.jsonl','human_intentions.jsonl','public_dialogue.jsonl','model_calls.jsonl','placement_evidence.jsonl','trace.jsonl'])]:hashes[str(path.relative_to(ROOT))]=sha256(path.read_bytes()).hexdigest()
    findings.append('<li>已完成的点心桌运行，人自选了饼干与盘两个目标，但只推进饼干，随后反复要求精确居中并重复请求空间。两个目标集合都没有变化，不能宣称本批出现了自主目标重组。</li>')
    findings.append('<li>π0.5工作空间运行，人持续观察、没有可测物体目标；机器人完成放置。这条是模型自行选择观察的实际结果，不算人的任务失败，也不能算活跃动态协作样本。</li>')
    findings.append('<li>OpenVLA工作空间场景在4秒自主提出两项目标、6秒保留推盘目标，11.55秒盘进入所选区域；但人手峰值1.988m/s、显示误差39.7mm，属于不合格诊断。动态意图证据保留，不能以其物理完成宣称合格协作。</li>')
    data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>自主个人目标 · 两种学习机器人</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:700px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style><main><header><h1>人自己选择目标，再与真实机器人共同活动</h1><p>不再定时告诉人该推哪个物体。Qwen根据自己的偏好、当前世界和执行经历，生成意图、目标、下一动作及公开协商提案。π0.5与OpenVLA分别实际运行，四段完整Sim视频与原始决定并列。</p></header>
<section><h2>本轮具体改变</h2><p>上一轮按预定时间给人更新工作要求。本轮只有点心桌/工作空间两种个人背景，没有人类物体任务或定时更新；人的目标集合由模型自己选择，可以保持、修订或放弃。目标和计划不会自动执行，当前动作也可选择观察、让行、暂离或返回。</p><p>个人偏好和自选目标只进入人模型；机器人只读自己的公开任务、实际相机/本体接口，以及人主动说出的消息和协商提案。提案不自动变成协议或任务分配，机器人以实际动作回应。场景中绿色/蓝色为盘区域，橙色/紫色为饼干区域；人可自己选择可见对象与目的地，不限定成推盘。</p><p>设置：task2/init0/seed0、independent倾向、episode记忆、45秒/20Hz、世界及人策略各初始化一次。Qwen3-14B每2秒推理；π0.5双相机+8维本体、最多执行10步，OpenVLA外相机+语言、每次1步，官方图像流程另行重建。推理时模拟时钟暂停。机器人用真实7维OSC动作，物体无吸附、无教师接管；人仍是运动学人体显示和力驱动指尖。</p><p class="notice">这是有限动作/目标区域内的自主意图实现，尚非整日开放活动或完整心理人类模型。只有两个背景、一个倾向和布局；人会随各算法的真实轨迹变化，不能当固定人轨迹配对或统计排名。OpenVLA此前静态人物参照也出现失败，不能将新失败独立归因于人的动态目标。</p></section>
<section><h2>实际结果</h2><div class="scroll"><table><tr><th>机器人/个人背景</th><th>可观察目标变化</th><th>新达成区间</th><th>人期末目标</th><th>机器人首次放置</th><th>机器人期末放置</th></tr>{''.join(table)}</table></div><ul>{''.join(findings)}</ul><p>目标变化按物体/区域几何关系计算，文字改写与区域别名不算新目标。选择时已有的关系不记新贡献；关系达成、位移和接触也不证明主观满意或严格因果归属。协商提案接通不等于机器人理解或同意。</p></section>
{''.join(panels)}<section><h2>怎样读这些视频</h2><p>视频直接录制真实Sim世界。同步面板展示模型长期意图、自己的目标、实际下一动作、公开提案及物体离目标的测量。请比较它说了什么与物体/身体实际如何变化；尤其区分换文字、换目标、换动作和真正到达。</p><p>人的关系达成要求25mm范围、25mm高度误差、低于0.08m/s持续0.2秒；无物体目标的主观意图不可用这一判据评价。机器人要求原生几何、碗盘实际接触、夹爪释放和持续稳定；首次达成与最终维持分开记录。</p><p><a href="evidence.json">原始结果及来源核查</a> · <a href="README.md">完整设置与边界</a> · <a href="../native_dynamic_activity_20261007/index.html">上一轮外部要求变化实测</a></p></section>
<section><h2>仍需推进</h2><p>完整手部抓持、身体碰撞、更多真实操作和场景、双方协商形成分工、长期偏好效度与统计协议仍缺。当前不合成cobalance总分，不将接口与记录核查当作模型能力证明。参考<a href="https://github.com/dannymcy/coopera_code/blob/main/HUMAN.md">COOPERA人类仿真</a>的偏好/意图/环境组织方向，未宣称复现其整日活动系统。</p></section></main>
<script>const runs={data};document.querySelectorAll('video[data-run]').forEach(video=>{{let target=document.getElementById('audit-'+video.dataset.run);const run=runs[video.dataset.run];function update(){{let decision=run.human[0],state=run.trace[0];for(const d of run.human)if(d.time_s<=video.currentTime)decision=d;for(const t of run.trace)if(t.time_s<=video.currentTime)state=t;let goals=decision.personal.personal_targets.map(g=>{{const p=state.objects[g.object_id],q=run.regions[g.destination];return `${{g.object_id}} → ${{g.destination}}：${{(Math.hypot(p[0]-q[0],p[1]-q[1])*1000).toFixed(1)}}mm`;}}).join('\\n');target.textContent=`人模型 ${{decision.time_s.toFixed(2)}}s · 自选意图：${{decision.personal.long_term_intention}}\n自己的目标：\n${{goals||'没有当前可测物体目标'}}\n实际选择：${{decision.decision.intent}} ${{decision.decision.object_id||''}} → ${{decision.decision.destination||''}}\n说：${{decision.decision.message}}\n协商提案：${{decision.proposals.map(p=>p.text).join('；')||'无'}}\n理由：${{decision.decision.reason}}\n实际身体y：${{state.human_position[1].toFixed(3)}}m；指尖y：${{state.human_hand_position[1].toFixed(3)}}m`;}}video.addEventListener('timeupdate',update);video.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'runs':evidence,'source_sha256':hashes},ensure_ascii=False,indent=2))
    print(HERE/'index.html')


if __name__=='__main__':main()
