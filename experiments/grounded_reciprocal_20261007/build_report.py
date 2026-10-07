"""真实感知、个人目标变化与双向视觉协调的运行报告。"""
from collections import Counter
from html import escape
import json
from pathlib import Path

from hrc_pilot.native_goal_evidence import goal_success
from hrc_pilot.video_verification import verify_result


ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
CASES=[('grounded_human_activity','bowl_on_stove','炉面工作与个人餐具整理'),
       ('grounded_human_activity','drawer_access','抽屉访问与个人取用安排'),
       ('grounded_human_activity','shared_serving','共同上桌与移动接收盘'),
       ('reciprocal_grounded_activity','bowl_on_stove','视觉协调器与个人整理的双向活动')]


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()
def tm(t):return '未出现' if t is None else f'{t:.2f}秒'


def main():
    panels=[];table=[];audits={};evidence={};facts=[]
    for family,key,label in CASES:
        run=RESULTS/family/key;ep=next(run.glob('task_*/init_000'));identifier=family+'__'+key
        gate=verify_result(run,require_timeline=True)
        if gate['status']!='verified':raise RuntimeError(f'真实视频未通过：{run}')
        names=['summary.json','provenance.json','model_execution_verification.json','avatar_verification.json','personal_verification.json',
               'human_feedback_verification.json','placement_verification.json','relative_geometry_verification.json',
               'scene_integrity_verification.json','continual_activity_verification.json','hand_robot_contact_verification.json','hand_verification.json']
        d={n:read(run/n) for n in names};assert not d['provenance.json']['source_files_changed_during_run']
        assert d['personal_verification.json']['status']=='verified'
        m=d['summary.json']['episodes'][0];continuous=d['continual_activity_verification.json']['episodes'][0]
        contact=d['hand_robot_contact_verification.json']['episodes'][0];human=rows(ep/'human_policy_io.jsonl');plans=rows(ep/'human_planner_io.jsonl')
        assert m['completion_time_s']==60 and m['native_actions']==1200
        model=Counter(h['parsed_decision']['intent'] for h in human)
        first_robot=next((r['time_s'] for r in rows(ep/'placement_evidence.jsonl') if goal_success(r)),None)
        events=[('原生目标首次稳定',first_robot),('双方当前目标首次稳定',continuous['first_joint_released_stable_s'])]
        events += [('人手／机械臂接触开始',contact['intervals'][0]['start_s'])] if contact['intervals'] else []
        revisions=m['personal_evidence']['goal_revisions']
        events += [('个人目标集合变化',r['start_s']) for r in revisions[1:]]
        buttons=''.join(f'<button data-video="{identifier}" data-seek="{t}">{escape(text)} · {t:.2f}秒</button>' for text,t in events if t is not None)
        coordinated=family=='reciprocal_grounded_activity'
        robot_plans=rows(ep/'robot_planner_io.jsonl') if coordinated else []
        if coordinated:d['coordination_verification.json']=read(run/'coordination_verification.json');assert d['coordination_verification.json']['status']=='verified'
        qualifies=d['model_execution_verification.json']['motion_eligible_episode_count']==1 and d['avatar_verification.json']['status']=='verified'
        table.append(f'<tr><td>{label}</td><td>{m["actual_vla_model_calls"]}／{m["hold_primitive_calls"]}</td><td>{len(robot_plans)}</td><td>{continuous["semantic_target_set_changes"]}</td><td>{continuous["human_released_goal_time_s"]:.2f}s</td><td>{continuous["joint_released_goal_time_s"]:.2f}s</td><td>{contact["hand_robot_contact_record_time_s"]:.2f}s</td></tr>')
        panels.append(f'''<article><h2>{label}</h2><p>{'Qwen3-VL视觉协调＋真实π0.5运动策略；机器人可公开回应并选择执行／保持。' if coordinated else '机器人为真实π0.5持续操作，人的目标与动作独立生成。'}场景60秒／20Hz，运动／显示资格{'通过' if qualifies else '未通过，作诊断展示'}。</p><video id="{identifier}" controls playsinline preload="metadata" poster="{link(ep/'preview.png')}" src="{link(ep/'demo.mp4')}"></video><div>{buttons}</div><div class="audit" id="audit-{identifier}"></div><p>人意图反思{len(plans)}次、动作推理{len(human)}次；实际动作{escape('、'.join(f'{k} {v}次' for k,v in model.items()))}。私人目标变化{continuous['semantic_target_set_changes']}次，原生目标首次稳定{tm(first_robot)}，双方关系累计维持{continuous['joint_released_goal_time_s']:.2f}秒。接触几何记录累计{contact['hand_robot_contact_record_time_s']:.2f}秒，直接接触清单进入人输入的决定数{contact['decision_count_with_direct_hand_contact_feedback']}。</p><p><a href="{link(ep/'human_planner_io.jsonl')}">意图最终答案与原始生成记录</a> · <a href="{link(ep/'human_policy_io.jsonl')}">原始动作选择</a> · <a href="{link(run/'personal_verification.json')}">目标与公开／私有边界</a> · <a href="{link(run/'hand_robot_contact_verification.json')}">手／机械臂接触时段</a> · <a href="{link(run/'continual_activity_verification.json')}">持续关系</a></p></article>''')
        audits[identifier]={'decisions':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'goals':h['personal_goal_state'],
                      'feedback':json.loads(h['public_input'].split('\n',1)[1])['your_measured_execution'],'planner_id':h['planner_decision_id']} for h in human],
                       'plans':[{'time_s':p['time_s'],'plan':p['active_intention_plan'],'error':p['validation_error']} for p in plans],
                       'frames':read(ep/'video_timeline.json')['frames'],
                       'robot':[{'time_s':p['time_s'],'decision':p['decision']} for p in robot_plans]}
        evidence[identifier]={**d,'video':gate};facts.append({'activity':label,'human_goal_changes':continuous['semantic_target_set_changes'],
                       'human_goal_time_s':continuous['human_released_goal_time_s'],'joint_time_s':continuous['joint_released_goal_time_s'],
                       'contact_record_time_s':contact['hand_robot_contact_record_time_s'],'robot_neural_decisions':len(robot_plans)})
    data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>可信感知与双向共同活动</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px;overflow-wrap:anywhere}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section,article{{background:white;padding:24px;margin:22px 0;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px);line-height:1.4}}h2{{font-size:24px}}video{{width:100%;max-height:630px;background:#132d34;border-radius:8px}}a{{color:#13786e}}button{{font:inherit;cursor:pointer;background:#e7f2ee;color:#214840;border:1px solid #9dbbb1;border-radius:6px;padding:7px 12px;margin:7px 8px 0 0}}button:focus-visible{{outline:3px solid #ce952d}}.notice{{background:#fff1d8;padding:17px;border-radius:8px}}.audit{{white-space:pre-wrap;background:#eff5f2;padding:17px;border-left:4px solid #368f7c}}.scroll{{overflow-x:auto}}table{{width:100%;min-width:860px;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 14px}}}}</style><main><header><h1>可信感知、私人安排与双向协调</h1><p>四段完整60秒共同活动，三机位直接录制。人的输入区分真实测量与旧解释，机器人也开始通过视觉模型生成公开回应与行动选择。</p></header>
<section><h2>为什么推进这一轮</h2><p>此前两阶段人模型常重复自己的旧解释，或处理机器人的对象。本轮将位置、接触、握持、公开分工与近期实际状态集中为事实；过去生成的解释不作为动作证据。意图推理启用本地Qwen3推理模式，动作仍单步自主选择；原始模型输出和最终结构化答案分开保留。目标可以是区域或当前接收物的on关系，不再只能登记初始化固定坐标。</p><p>程序不按计划列表或分数给双方选任务，没有定时人动作／目标变更。人可以继续、调整目标、暂缓、让行或询问；最终判断仍看实际物理行为。</p></section>
<section><h2>设置与观看方式</h2><p>三基础场景：碗放炉面、打开中层抽屉与共同上桌。π0.5读取两路真实相机／本体和公开语言，人为Qwen3-14B；independent、episode、init0／seed0、60秒／20Hz。每6秒意图反思，每2秒动作选择，收到新公开消息可重观察；推理期间模拟时钟暂停。</p><p>最后一条另外提供双方自身的实际接触，并接入Qwen3-VL-8B视觉协调器。它只读自己的相机／本体／接触、公开任务／对话与自己历史，不能读人的私人目标／偏好或成绩。execute由真实VLA运动，hold是模型选择的姿态保持原语，不能伪装成学习VLA动作。</p><p>广角＋原始外部／腕部相机同一时刻直接录制，896×512／20fps；可拖动、定位事件、同步查看人的目标与实际反馈。不是轨迹动画，也不是事后重渲染。4条世界各初始化一次，持续期间没有重置。</p><p class="notice">两批算法与接触感知不同，采样未严格配对，不能据此做因果或算法排名。人获得理想几何、人物是骨骼显示／双指受力手代理，完整身体／五指、带负载容器操作及真实心理效度尚未验证。</p></section>
<section><h2>实际维持与相互接触</h2><div class="scroll"><table><tr><th>活动</th><th>VLA／保持块</th><th>机器人协调推理</th><th>人目标变化</th><th>个人满足时长</th><th>双方维持时长</th><th>手／机械臂接触记录</th></tr>{''.join(table)}</table></div><p>语义目标变化不等于成功或真实心理变化。区域关系与相对接收物关系分别测量真实接触／松手与稳定；空目标不算成功。接触时长只计记录中几何distance<=0，不代表接触力、伤害或唯一阻挡原因。</p></section>{''.join(panels)}
<section><h2>已有发现与解释边界</h2><p>基础炉面场景中，人选择自己的餐盘，但掌部与机械臂第6／7连杆接触，下降阶段未完成；不能把这类阻挡和选择错误混为一谈。基础抽屉场景18秒移除餐盘目标、42秒又加回，说明本次优先事项集合确有自主变化，但未因此完成个人整理。三基础场景中，直接的手／机器人接触清单尚未进入人的输入，不能把随后新增感知用于重写它们的结果。</p><p>双向场景的回应、执行与保持来自真实视觉模型选择；提案、计划文字和声称完成都不自动成为物理成功。是否有效重新组织活动，需同时看双方实际目标、动作与持续关系，不能仅凭更多对话或绿色链路核验认定cobalance。</p><p><a href="README.md">完整结果与仍未完成项</a> · <a href="PLAN.md">运行协议</a> · <a href="evidence.json">原始结果及来源</a> · <a href="../reflective_activity_20261007/index.html">上一批分层人策略与独立抓放</a></p></section></main>
<script>const runs={data};for(const [key,run] of Object.entries(runs)){{const v=document.getElementById(key),out=document.getElementById('audit-'+key);function update(){{let f=run.frames[0];for(const r of run.frames)if(r.video_time_s<=v.currentTime)f=r;let d=run.decisions[0];for(const r of run.decisions)if(r.time_s<=f.benchmark_time_s)d=r;const p=run.plans[d.planner_id];let robot=null;for(const r of run.robot)if(r.time_s<=f.benchmark_time_s)robot=r;out.textContent=`模拟 ${{f.benchmark_time_s.toFixed(2)}}秒 · 意图反思 ${{p.time_s.toFixed(2)}}秒 · 动作选择 ${{d.time_s.toFixed(2)}}秒\n私人目标：${{JSON.stringify(d.goals.personal_targets)}}\n长期意图：${{p.plan.long_term_intention||''}}\n反思观察：${{JSON.stringify(p.plan.observed_changes||'')}}\n选择：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n理由：${{d.decision.reason}}\n收到的阶段：${{d.feedback.motor_phase}}；在手：${{d.feedback.object_measured_in_hand||'无'}}\n手部接触感知：${{JSON.stringify(d.feedback.hand_contact_report||'本版本未提供直接清单')}}\n人公开说：${{d.decision.message}}\n机器人最新选择：${{robot?JSON.stringify(robot.decision):'原生VLA持续控制'}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}document.querySelectorAll('button[data-seek]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.video).currentTime=Number(b.dataset.seek)));</script></html>'''
    HERE.mkdir(parents=True,exist_ok=True);(HERE/'index.html').write_text(html)
    artifacts=RESULTS.resolve().parent/'report_snapshots/grounded_reciprocal_20261007';artifacts.mkdir(parents=True,exist_ok=True)
    (artifacts/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'formal_videos':4,'runs':evidence,'facts':facts},ensure_ascii=False,indent=2))
    if not (HERE/'evidence.json').exists():(HERE/'evidence.json').symlink_to(artifacts/'evidence.json')
    print(json.dumps(facts,ensure_ascii=False))


if __name__=='__main__':main()
