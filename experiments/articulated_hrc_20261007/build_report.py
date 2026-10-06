"""真实双指抓放、高台任务和生成式伙伴的可审计视频报告。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
CASES={'snack_storage':'个人点心高台收纳','shared_serving':'接收盘与共同上桌'}


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()
def tm(v):return '未观察到' if v is None else f'{v:.2f}s'


def main():
    panels=[];table=[];evidence={};hashes={};audits={};calibration=[]
    for name,label in [('articulated_hand_validation','初始碰撞阻挡诊断'),('articulated_hand_formal','修订布局后的独立真实抓放校准')]:
        root=RESULTS/name;ep=root/'hand_validation'
        video=read(root/'video_verification.json');hand=read(root/'hand_verification.json')
        assert video['status']=='verified'
        calibration.append(f'''<article><h2>{label}</h2><p>命令来自校准教师、机器人原地；不是学习策略或HRC成绩。双指接触抬起{tm(hand['episodes'][0]['first_bilateral_contact_lift_s'])}；释放接触高台{tm(hand['episodes'][0]['first_released_support_contact_s'])}；手峰速{hand['episodes'][0]['human_peak_speed_m_s']:.3f}m/s。</p><video controls preload="metadata" poster="{link(ep/'preview.png')}" src="{link(ep/'demo.mp4')}"></video><p><a href="{link(root/'hand_verification.json')}">接触与实际位移核查</a></p></article>''')
        evidence[name]={'video':video,'hand':hand,'metrics':read(ep/'metrics.json')}
    for case,label in CASES.items():
        root=RESULTS/'articulated_hrc'/case;ep=root/'task_02/init_000'
        names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json','avatar_verification.json',
               'human_feedback_verification.json','placement_verification.json','personal_verification.json','prompt_token_verification.json','hand_verification.json','storage_verification.json']
        d={n:read(root/n) for n in names}
        assert d['video_verification.json']['status']=='verified' and d['personal_verification.json']['status']=='verified'
        assert not d['provenance.json']['source_files_changed_during_run']
        m=d['summary.json']['episodes'][0];human=rows(ep/'human_policy_io.jsonl');trace=rows(ep/'trace.jsonl')
        modes=Counter(h['parsed_decision']['intent'] for h in human)
        hand=d['hand_verification.json']['episodes'];valid=d['model_execution_verification.json']['motion_eligible_episode_count']==1 and d['avatar_verification.json']['qualified_count']==1
        first_robot=next((p['time_s'] for p in rows(ep/'placement_evidence.jsonl') if p['released_stable_placement']),None)
        storage=d['storage_verification.json']['episodes'][0]
        human_status=('满足' if storage['released_goal_evidence']['human_current_observable_goals_satisfied'] else '未满足') if m['human_goal_evaluable'] else '不可评'
        table.append(f'<tr><td>{label}{"（诊断）" if not valid else ""}</td><td>{sum(h["first_bilateral_contact_lift_s"] is not None for h in hand)}</td><td>{sum(h["first_released_support_contact_s"] is not None for h in hand)}</td><td>{human_status}</td><td>{tm(first_robot)}</td><td>{int(m["robot_goal_success"])}</td><td>{tm(storage["first_joint_released_stable_s"])}</td><td>{int(storage["final_joint_released_stable"])}</td></tr>')
        audits[case]={'decisions':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'personal':h['personal_goal_state'],
                                  'measured':json.loads(h['public_input'].split('\n',1)[1])['your_measured_execution']} for h in human]}
        hand_text='；'.join(f'{h["object_id"]}：接触抬起{tm(h["first_bilateral_contact_lift_s"])}，释放到高台{tm(h["first_released_support_contact_s"])}' for h in hand)
        panels.append(f'''<article><h2>{label}</h2><p>π0.5真实调用{m['actual_vla_model_calls']}次，人模型决定{len(human)}次，模拟{m['completion_time_s']:.1f}秒；运动/显示资格{'通过' if valid else '未通过，仅诊断'}。人的当前可观察目标{human_status}，机器人期末放置{'完成' if m['robot_goal_success'] else '未完成'}。</p><video data-case="{case}" controls preload="metadata" poster="{link(ep/'preview.png')}" src="{link(ep/'demo.mp4')}"></video><div class="audit" id="audit-{case}"></div><p>{escape(hand_text)}。</p><p>首次双方释放稳定完成{tm(storage['first_joint_released_stable_s'])}；期末{'仍共同完成' if storage['final_joint_released_stable'] else '未维持共同完成'}。原始仅位置判据共同结果{int(storage['raw_position_joint_predicate'])}单独保留，当前表格使用支撑接触及释放审计。</p><p>模型动作：{escape('、'.join(f'{k} {v}次' for k,v in modes.items()))}。公开提案{m['personal_evidence']['public_negotiation_proposals']}条；无效目标参数{m['personal_evidence']['target_validation_errors']}次。握持、释放、物理关系和任务成功各自核查，不凭文字确认记成功。</p><p><a href="{link(ep/'human_policy_io.jsonl')}">人的原始输入输出</a> · <a href="{link(ep/'personal_evidence.json')}">自选目标结果</a> · <a href="{link(root/'hand_verification.json')}">手抓放接触</a> · <a href="{link(root/'model_execution_verification.json')}">实际控制与速度</a></p></article>''')
        evidence[case]=d
        for p in [*(root/n for n in names),*(ep/n for n in ['human_policy_io.jsonl','personal_evidence.json','trace.jsonl','scene.xml'])]:hashes[str(p.relative_to(ROOT))]=sha256(p.read_bytes()).hexdigest()
    data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真实抓放与高台共同活动</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:700px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style><main><header><h1>从指尖推物到真实抓取、搬运和释放</h1><p>新增受力双指接触手与实际高8cm的收纳台。独立校准证明摩擦抓放，再让Qwen自选目标和动作，与真实π0.5机械臂共同活动。四段运行时Sim视频，校准与模型实验分开呈现。</p></header>
<section><h2>目的与新增能力</h2><p>之前人的动作只有推物，新策略场景仍受限，而且出现过1.988m/s超速。本轮增加实际XYZ、腕部yaw、双指关节，手通过接触和摩擦夹住物体，支持grasp、place、release；不绑定、焊接或搬写物体坐标。控制器加入有效惯性和限速速度跟踪，继续保留原0.65m/s速度和25mm显示门槛。</p><p>新高台让目标有实际高度差，推物无法直接完成。点心收纳背景中，人希望自己的饼干在高台；共同上桌背景中，人希望把餐盘移到高台，可观察机械臂是否放好碗再选择动作。机器人仍负责原生黑碗放盘，人的私有偏好不直接给机器人，只有公开话语进入其语言输入。</p><p>两个模型实验各40秒、20Hz，Qwen3-14B每2秒决定，π0.5最多10步后重观察；世界/人策略只初始化一次。意图、目标、grasp/place和时机由模型选择，程序不依据分数挑动作；plan不会自动路由。生成推理期间模拟时钟暂停。</p><p class="notice">这是接触手代理与原生具身模型的系统实测，不是完整五指/人体动力学。皮肤仍为完整骨骼运动学显示，没有完整身体碰撞；少量场景不能证明人格效度、协商理解或cobalance能力。校准教师不是Benchmark策略，生成命令不是实际成功。</p></section>
<section><h2>模型实验结果</h2><div class="scroll"><table><tr><th>背景</th><th>接触抬起物体数</th><th>高台释放物体数</th><th>人期末目标</th><th>机器人首次放置</th><th>机器人期末放置</th><th>首次共同完成</th><th>期末共同完成</th></tr>{''.join(table)}</table></div><p>接触抬起要求两指实际接触、物体抬高4cm以上；高台释放要求物体实际接触支撑面且双指不再接触。人的目标关系和机器人放置另行判定，不将原语结束或生成说明等同共同成功。</p></section>
<section><h2>本批实际结果</h2><p>点心收纳：人自主抓饼干、搬运并释放到高台，14.95秒双方均满足释放稳定任务关系；但之后人重复抓放，40秒末帧仍夹持饼干，所以期末不能记为收纳完成。原先仅位置接近的结果为真，被此次独立释放/支撑审计区分，旧轨迹和输入未覆盖。</p><p>共同上桌：人没有按背景去移动接收盘，而是把机器人的黑碗任务当成自己的工作，20次选择grasp，与机械臂竞争同一物体；手始终未形成双指抬起，机器人也没有有效放置。模型未按实际进度重新协调，抓取原语还曾沿用已移动物体的旧接近点；因此失败包含分工误读和低层移动目标适配问题，不能单独归为具身模型HRC能力。失败完整保留。</p><p>两条模型运行的手峰速均约0.196m/s、人物对齐通过；这证明本批条件下没有此前超速，不能外推所有接触与人体安全条件。</p></section>{''.join(panels)}<section><h2>独立物理校准与原始失败</h2><p>首条发现高台初始位置与盘重叠、张手过宽导致下降阻挡，未抬起物体；保留诊断。修订布局和按碰撞几何开指后，7.25秒双指接触并抬起，13.15秒释放到高台；物体最大抬升12.43cm，手/物体峰速约0.196/0.197m/s，人物显示核查通过。此结果只证明该校准条件下执行器可用。</p></section>{''.join(calibration)}<section><h2>证据与仍需推进</h2><p>视频逐帧解码及时间轴复核，实际输入/动作/控制、人的反馈、双指接触、抬升和释放独立重建；失败完整保留，运动资格与任务完成分开。仍需扩展场景、操作和模型，验证真实人体/长期人类策略与双方协商，完整目标尚未完成。</p><p><a href="evidence.json">结果及来源</a> · <a href="README.md">完整设置与边界</a> · <a href="../autonomous_human_20261007/index.html">上一批自选目标与超速诊断</a></p></section></main>
<script>const runs={data};document.querySelectorAll('video[data-case]').forEach(v=>{{const target=document.getElementById('audit-'+v.dataset.case),run=runs[v.dataset.case];function update(){{let d=run.decisions[0];for(const r of run.decisions)if(r.time_s<=v.currentTime)d=r;target.textContent=`人模型 ${{d.time_s.toFixed(2)}}s · ${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n自己的目标：${{JSON.stringify(d.personal.personal_targets)}}\n说：${{d.decision.message}}\n理由：${{d.decision.reason}}\n实际运动阶段：${{d.measured.motor_phase}}\n双指实际接触：${{JSON.stringify(d.measured.measured_finger_target_contacts)}}\n测得在手：${{d.measured.object_measured_in_hand||'无'}}\n运动反馈：${{d.measured.motor_failure||'无异常反馈'}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'runs':evidence,'source_sha256':hashes},ensure_ascii=False,indent=2))
    print(HERE/'index.html')


if __name__=='__main__':main()
