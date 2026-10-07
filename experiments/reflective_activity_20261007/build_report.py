"""以同步三机位视频报告生成式人意图、实际动作与持续共同结果。"""
from collections import Counter
from html import escape
import json
from pathlib import Path

from hrc_pilot.video_verification import verify_result
from hrc_pilot.native_goal_evidence import goal_success


ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
CASES={'food_into_bowl':'共享厨房：奶酪包入碗','drawer_access':'共享柜台：打开中层抽屉',
       'shared_serving_pi':'共同上桌与高台：π0.5','shared_serving_openvla':'共同上桌与高台：OpenVLA'}


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def href(p):return '../../'+p.relative_to(ROOT).as_posix()
def tm(t):return '未出现' if t is None else f'{t:.2f}秒'


def video(ep,identifier,events):
    buttons=''.join(f'<button data-video="{identifier}" data-seek="{t}">{escape(label)} · {t:.2f}秒</button>' for label,t in events if t is not None)
    return f'<video id="{identifier}" controls playsinline preload="metadata" poster="{href(ep/"preview.png")}" src="{href(ep/"demo.mp4")}"></video><div>{buttons}</div>'


def main():
    panels=[];table=[];audits={};evidence={};formal_videos=0;calibration=[];facts=[]
    for key,label in CASES.items():
        root=RESULTS/'reflective_hrc'/key;ep=next(root.glob('task_*/init_000'))
        gate=verify_result(root,require_timeline=True)
        if gate['status']!='verified':raise RuntimeError(f'缺完整重要实验视频：{root}')
        formal_videos+=gate['verified_episode_count']
        names=['summary.json','provenance.json','model_execution_verification.json','avatar_verification.json',
               'human_feedback_verification.json','personal_verification.json','placement_verification.json',
               'relative_geometry_verification.json','scene_integrity_verification.json','continual_activity_verification.json','hand_verification.json']
        d={name:read(root/name) for name in names};m=d['summary.json']['episodes'][0]
        assert not d['provenance.json']['source_files_changed_during_run']
        assert d['personal_verification.json']['status']=='verified'
        assert m['native_actions']==1200 and m['completion_time_s']==60.
        runtime=read(ep/'runtime_plan.json');assert runtime['actual_environment_ignore_done'] and runtime['actual_environment_horizon']>1210
        metric=d['continual_activity_verification.json']['episodes'][0]
        integrity=d['scene_integrity_verification.json']['episodes'][0]
        losses=[o for o in integrity['objects'] if o['first_sustained_below_table_clearance_s'] is not None]
        first_robot=next((r['time_s'] for r in rows(ep/'placement_evidence.jsonl') if goal_success(r)),None)
        human=rows(ep/'human_policy_io.jsonl');plans=rows(ep/'human_planner_io.jsonl')
        commands=Counter(r['parsed_decision']['intent'] for r in human)
        kinds=Counter(r['active_intention_plan'].get('decision_kind','未接受') for r in plans)
        qualified=(d['model_execution_verification.json']['motion_eligible_episode_count']==1 and d['avatar_verification.json']['status']=='verified')
        model=d['provenance.json']['model_server_metadata']['config']
        table.append(f'<tr><td>{label}</td><td>{len(plans)}／{len(human)}</td><td>{metric["semantic_target_set_changes"]}</td><td>{metric["human_goal_evaluable_time_s"]:.1f}s</td><td>{metric["robot_physical_goal_time_s"]:.1f}s</td><td>{metric["joint_released_goal_time_s"]:.1f}s</td><td>{len(losses)}</td></tr>')
        events=[('原生目标首次稳定',first_robot),('双方当前目标首次稳定',metric['first_joint_released_stable_s'])]
        events += [(o['object_id']+'低于桌面',o['first_below_table_clearance_s']) for o in losses]
        events += [('反思提出调整',p['time_s']) for p in plans if p['active_intention_plan'].get('decision_kind')=='revise']
        panels.append(f'''<article><h2>{label}</h2><p>真实机器人：{escape(model)}；60秒、1200个实际动作。手／目标物／人物运动显示资格：{'通过' if qualified else '未通过，仅诊断'}。</p>{video(ep,key,events)}<div class="audit" id="audit-{key}"></div><p>反思模型{len(plans)}次，动作模型{len(human)}次，均为同一本地Qwen3-14B的独立推理。反思类型：{escape('、'.join(f'{k} {v}次' for k,v in kinds.items()))}；实际动作：{escape('、'.join(f'{k} {v}次' for k,v in commands.items()))}。</p><p>原生目标首次{tm(first_robot)}；双方当前目标首次{tm(metric['first_joint_released_stable_s'])}、累计维持{metric['joint_released_goal_time_s']:.2f}秒，期末{'成立' if metric['final_joint_released_stable'] else '未成立'}。人的无可评分目标时长{metric['human_goal_unevaluable_time_s']:.2f}秒，不能当作成功。</p><p>从初始世界新达到的个人关系{metric['new_relations_from_episode_start_count']}个；语义目标变化{metric['semantic_target_set_changes']}次，双方维持关系失去{metric['joint_goal_loss_transitions']}次。完整库存持续低于桌面的物品{len(losses)}个。</p><p><a href="{href(ep/'human_planner_io.jsonl')}">原始意图反思</a> · <a href="{href(ep/'human_policy_io.jsonl')}">原始动作推理</a> · <a href="{href(root/'personal_verification.json')}">目标来源与公开边界</a> · <a href="{href(root/'continual_activity_verification.json')}">逐时刻持续关系</a> · <a href="{href(root/'scene_integrity_verification.json')}">物品损失</a></p></article>''')
        audits[key]={'decisions':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'goals':h['personal_goal_state'],
                                 'received_execution':json.loads(h['public_input'].split('\n',1)[1])['your_measured_execution'],
                                 'planner_id':h['planner_decision_id']} for h in human],
                     'plans':[{'time_s':p['time_s'],'plan':p['active_intention_plan'],'validation_error':p['validation_error']} for p in plans],
                     'frames':read(ep/'video_timeline.json')['frames']}
        evidence[key]={**d,'video':gate,'runtime_plan':runtime}
        facts.append(f'{label}：原生目标维持{metric["robot_physical_goal_time_s"]:.1f}s，双方维持{metric["joint_released_goal_time_s"]:.1f}s，个人目标变化{metric["semantic_target_set_changes"]}次，物品损失{len(losses)}个。')
    root=RESULTS/'reflective_hand_calibration';hand=read(root/'hand_verification.json');avatar=read(root/'avatar_verification.json')
    gate=verify_result(root,require_timeline=True)
    if gate['status']!='verified':raise RuntimeError('独立校准视频不完整')
    formal_videos+=gate['verified_episode_count']
    for h in hand['episodes']:
        ep=Path(h['episode']);ep=ROOT/ep if not ep.is_absolute() else ep
        m=read(ep/'metrics.json');name=h['object_id']
        calibration.append(f'<article><h3>{escape(name)} · 独立操作校准</h3><p>教师命令、机器人原地，不计学习策略／HRC成绩。双指抬起{tm(h["first_bilateral_contact_lift_s"])}、抓取后支撑释放{tm(h["first_released_support_contact_s"])}，最大抬升{h["maximum_object_lift_m"]*100:.2f}cm，末阶段{escape(m["terminal_phase"])}。</p>{video(ep,"cal-"+name,[("双指抬起",h["first_bilateral_contact_lift_s"]),("支撑释放",h["first_released_support_contact_s"])])}</article>')
    evidence['calibration']={'video':gate,'hand':hand,'avatar':avatar}
    diagnostic=read(RESULTS/'reflective_diagnostic_catalog.json')
    diagnostic_links=''.join(f'<li>{escape(d["family"])}／{escape(Path(d["episode"]).parents[1].name)}：'
        f'<a href="../../{d["episode"]}/demo.mp4">中断片段</a>，{d.get("decoded_frames",0)}帧；'
        f'原始反思／动作日志{"已保存" if d["raw_reflection_io_available"] else "缺失"}，不计正式成绩。</li>' for d in diagnostic['episodes'])
    evidence['diagnostics']=diagnostic
    data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>意图反思与真实共同活动</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px;overflow-wrap:anywhere}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section,article{{background:white;padding:24px;margin:22px 0;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px);line-height:1.4}}h2{{font-size:25px}}h3{{font-size:21px}}video{{width:100%;max-height:630px;background:#132d34;border-radius:8px}}a{{color:#13786e}}button{{font:inherit;cursor:pointer;background:#e7f2ee;color:#214840;border:1px solid #9dbbb1;border-radius:6px;padding:7px 12px;margin:7px 8px 0 0}}button:focus-visible{{outline:3px solid #ce952d}}.notice{{background:#fff1d8;padding:17px;border-radius:8px}}.audit{{white-space:pre-wrap;background:#eff5f2;padding:17px;border-left:4px solid #368f7c}}.scroll{{overflow-x:auto}}table{{width:100%;min-width:840px;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}.flow{{display:flex;gap:12px;flex-wrap:wrap}}.flow span{{padding:12px;background:#e7f2ee;border-radius:8px}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 14px}}}}</style><main>
<header><h1>让较长期意图与当前动作分别接受真实世界的检验</h1><p>三类共同活动、两种学习机器人、四段60秒运行。人的目标与动作均由模型选择；四段独立操作校准。八段完整同步三机位Sim视频。</p></header>
<section><h2>本轮推进的是人的策略</h2><p>上一轮人会重复旧解释和抓取，计划文字也没有实际执行。本轮由意图模型定期比较自己的假设、实际位置／接触与对方活动，再由动作模型根据当前意图和最新反馈选择一个动作。两次都是独立神经推理，使用同一Qwen权重；不是两个参数独立的模型。</p><div class="flow"><span>实际感知与自身经历</span><span>→ 较长期意图反思（约6秒）</span><span>→ 当前动作推理（约2秒）</span><span>→ 受力接触手</span></div><p>推理调度不要求定时换目标；计划不作为执行器队列，程序不按分数选择双方下一任务。模型可以保持、调整、暂缓或结束活动。目标和自己的解释仍可能错误，必须看实际动作。</p><p>四种物品现在都有独立接触抓放见证：按碰撞包络留出掌部高度，保持真实碰撞；张手后根据实际手指脱离退出释放阶段。没有绑定、焊接或搬写物体坐标。校准只证明这些条件下的执行器前提。</p></section>
<section><h2>看视频前先了解设置</h2><p>各模型场景持续60秒／20Hz、init0／seed0。奶酪与抽屉使用原生goal任务，共同上桌使用两种权重均支持的spatial任务2；人的偏好与公开交流影响场景，世界与策略只初始化一次。默认按1倍模拟时间播放，推理时模拟时钟暂停，视频长度不等于计算耗时。</p><p>左侧广角展示人、机械臂与环境；右侧记录外部相机和腕部相机，可看清柜体遮挡的操作。π实际消费两路相机／本体；OpenVLA实际消费外部相机与语言，其腕图／本体仅兼容记录。相机画面来自同一时刻的运行记录，不是轨迹补画。</p><p class="notice">人与机械臂使用不同感知：人获得理想几何与接触，机器人读取相机。人物是骨骼显示与双指接触手代理，尚非完整五指／身体动力学。公开话语追加到VLA输入的方式属于本实验配置，不能等同官方LIBERO排名。</p></section>
<section><h2>持续结果，不能只看末帧</h2><div class="scroll"><table><tr><th>活动</th><th>反思／动作推理</th><th>人目标变化</th><th>人可评分时长</th><th>原生目标维持</th><th>双方目标维持</th><th>物品损失</th></tr>{''.join(table)}</table></div><p>个人关系需目标区域、真实支撑、双方手部无接触、物体速度低于0.08m/s连续稳定0.2秒；原生任务另核查放置／关节条件。空目标不可评分，别名不算目标变化，初始已满足的位置不计新关系。目标难度和可评分时长可能不同，这些数值描述本次运行，不能直接化为算法排名。</p></section>{''.join(panels)}
<section><h2>独立抓放校准</h2><p>下面四条30秒记录均由教师发出抓／放命令，用来检查工具可用性；不能混入生成式人策略成绩或模型训练专家标签。</p></section>{''.join(calibration)}
<section><h2>证据与仍未完成的范围</h2><p>视频逐帧解码／时间轴、输入像素／本体／原始动作／实际控制、人两阶段原始输出、目标来源与公开边界、人物显示与完整库存损失均独立核查。参照<a href="https://github.com/dannymcy/coopera_code/blob/main/HUMAN.md">COOPERA的人模拟组织</a>，本批自建实时反思闭环，未复现整日心理生成、真实人格校准或完整人体动作。</p><p>初始60秒运行曾受到原生约50秒时限阻断；修复后环境实际horizon为1211、ignore_done开启，完整60秒在同一世界推进，没有重置场景。另一批诊断发现同义目标对数组被严格字典接口拒绝，已修复解码并记录协议；两批中断、原始视频和可保存输出保留，未混入八段正式覆盖率。</p><details><summary>保留的接口／时限诊断</summary><ul>{diagnostic_links}</ul></details><p>完整Benchmark目标与研究效度仍未证明。需要可靠的人策略效度、更多任务／时间尺度／模型／人格与统计覆盖，以及关系目标和完整身体能力。人的意图变化、协商提案或局部成功不能单独证明HRC/cobalance。</p><p><a href="PLAN.md">运行协议与解释边界</a> · <a href="README.md">完整实测说明</a> · <a href="evidence.json">结果与来源</a> · <a href="../relative_placement_20261007/index.html">上一批相对放置与物品损失</a></p></section></main>
<script>const runs={data};for(const [key,run] of Object.entries(runs)){{const v=document.getElementById(key),out=document.getElementById('audit-'+key);function update(){{let f=run.frames[0];for(const r of run.frames)if(r.video_time_s<=v.currentTime)f=r;const t=f.benchmark_time_s;let d=run.decisions[0];for(const r of run.decisions)if(r.time_s<=t)d=r;const p=run.plans[d.planner_id];out.textContent=`模拟 ${{t.toFixed(2)}}秒 · 意图反思 ${{p.time_s.toFixed(2)}}秒 · 动作选择 ${{d.time_s.toFixed(2)}}秒\n反思类型：${{p.plan.decision_kind||'未接受'}}\n长期意图：${{p.plan.long_term_intention||''}}\n个人目标：${{JSON.stringify(d.goals.personal_targets)}}\n反思观察：${{JSON.stringify(p.plan.observed_changes||'')}}\n旧假设纠正：${{JSON.stringify(p.plan.assumption_corrections||'')}}\n选择当前动作：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n动作理由：${{d.decision.reason}}\n当时收到的阶段：${{d.received_execution.motor_phase}}；实际握持：${{d.received_execution.object_measured_in_hand||'无'}}\n公开说：${{d.decision.message}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}document.querySelectorAll('button[data-seek]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.video).currentTime=Number(b.dataset.seek)));</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'formal_video_count':formal_videos,'runs':evidence,'facts':facts},ensure_ascii=False,indent=2))
    print(json.dumps({'formal_videos':formal_videos,'facts':facts},ensure_ascii=False))


if __name__=='__main__':main()
