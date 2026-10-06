"""跨物体/支撑面/关节的真实动态伙伴任务报告，不合成未经验证的HRC排名。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

from hrc_pilot.native_scene_catalog import CASES
from hrc_pilot.native_goal_evidence import goal_success

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def href(p):return '../../'+p.relative_to(ROOT).as_posix()
def tm(value):return '未观察到' if value is None else f'{value:.2f}s'


def main():
    panels=[];refs=[];table=[];audit={};evidence={};hashes={};findings=[]
    object_roles=read(RESULTS/'scene_catalog_human/object_role_verification.json')
    for key,case in CASES.items():
        reference=RESULTS/'scene_catalog_reference'/key;root=RESULTS/'scene_catalog_human'/key
        ref_m=read(reference/'summary.json')['episodes'][0]
        ref_ep=reference/f'task_{case.task_id:02d}/init_000';ep=root/f'task_{case.task_id:02d}/init_000'
        ref_v=read(reference/'video_verification.json');assert ref_v['status']=='verified'
        names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json','avatar_verification.json',
               'human_feedback_verification.json','placement_verification.json','personal_verification.json','prompt_token_verification.json','hand_verification.json']
        d={n:read(root/n) for n in names}
        assert d['video_verification.json']['status']=='verified' and d['personal_verification.json']['status']=='verified'
        assert not d['provenance.json']['source_files_changed_during_run']
        m=d['summary.json']['episodes'][0];human=rows(ep/'human_policy_io.jsonl');goals=rows(ep/'placement_evidence.jsonl')
        first=next((r['time_s'] for r in goals if goal_success(r)),None)
        valid=d['model_execution_verification.json']['motion_eligible_episode_count']==1 and d['avatar_verification.json']['qualified_count']==1
        hstatus=('满足' if m['human_goal_success'] else '未满足') if m['human_goal_evaluable'] else '无可测目标'
        table.append(f'<tr><td>{case.label}{"（仅诊断）" if not valid else ""}</td><td>{int(ref_m["task_success"])}</td><td>{tm(first)}</td><td>{int(m["robot_goal_success"])}</td><td>{hstatus}</td><td>{m["personal_evidence"]["observable_target_set_changes"]}</td></tr>')
        modes=Counter(r['parsed_decision']['intent'] for r in human)
        audit[key]={'decisions':[{'time_s':r['time_s'],'decision':r['parsed_decision'],'personal':r['personal_goal_state'],
                                'measured':json.loads(r['public_input'].split('\n',1)[1])['your_measured_execution']} for r in human]}
        hand=d['hand_verification.json']['episodes']
        hand_text='；'.join(f'{r["object_id"]}：真实双指抬起{tm(r["first_bilateral_contact_lift_s"])}' for r in hand)
        qualification=('运动/显示通过' if valid else f'仅诊断：手峰速{d["model_execution_verification.json"]["episodes"][0]["human_peak_speed_m_s"]:.3f}m/s，显示对齐{d["avatar_verification.json"]["episodes"][0]["max_alignment_error_m"]*1000:.1f}mm')
        panels.append(f'''<article><h2>{case.label} · 生成式个人整理</h2><p>{escape(case.focus)}。{qualification}。机器人首次任务成立{tm(first)}、期末{'成立' if m['robot_goal_success'] else '未成立'}；人的当前可观察目标{hstatus}。</p><video data-case="{key}" controls preload="metadata" poster="{href(ep/'preview.png')}" src="{href(ep/'demo.mp4')}"></video><div class="audit" id="audit-{key}"></div><p>π真实调用{m['actual_vla_model_calls']}次，人决定{len(human)}次。人动作：{escape('、'.join(f'{k} {v}次' for k,v in modes.items()))}。{escape(hand_text)}。公开提案{m['personal_evidence']['public_negotiation_proposals']}条，目标参数错误{m['personal_evidence']['target_validation_errors']}次。</p><p><a href="{href(ep/'human_policy_io.jsonl')}">人原始输入输出</a> · <a href="{href(ep/'personal_evidence.json')}">个人目标物理关系</a> · <a href="{href(ep/'placement_evidence.jsonl')}">原生任务物理证据</a> · <a href="{href(root/'model_execution_verification.json')}">输入/控制/时钟与速度</a></p></article>''')
        refs.append(f'''<article><h2>{case.label} · 无人物基础操作参照</h2><p>{'完成' if ref_m['task_success'] else '未完成'}，模拟{ref_m['completion_time_s']:.2f}s，真实π推理{ref_m['actual_vla_model_calls']}次。首次实际物理成功后结束，无人物/标记/公开话语，不直接作为动态人影响的匹配控制。</p><video controls preload="metadata" poster="{href(ref_ep/'preview.png')}" src="{href(ref_ep/'demo.mp4')}"></video></article>''')
        findings.append(f'<li>{case.label}：人实际{escape("、".join(f"{k}{v}次" for k,v in modes.items()))}，自选目标集合改变{m["personal_evidence"]["observable_target_set_changes"]}次；机器人首次{tm(first)}、期末{int(m["robot_goal_success"])}；人的当前目标{hstatus}。</li>')
        evidence[key]={'reference':{'summary':ref_m,'video':ref_v,'provenance':read(reference/'provenance.json')},'human_condition':d}
        for p in [*(root/n for n in names),*(ep/n for n in ['human_policy_io.jsonl','personal_context.json','personal_evidence.json','scene.xml','trace.jsonl'])]:hashes[str(p.relative_to(ROOT))]=sha256(p.read_bytes()).hexdigest()
    data=json.dumps(audit,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>跨物体和关节操作 · 动态伙伴任务集</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:750px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style><main><header><h1>不止黑碗：食物、酒瓶、炉面和抽屉的共同活动</h1><p>四类实际厨房任务，四段生成式伙伴视频与四段基础操作参照。人的物品/区域从真实场景库存读取，当前目标与动作由Qwen选择；机器人使用真实π0.5动作，没有教师接管或吸附。</p></header>
<section><h2>这轮扩展了什么</h2><p>此前场景主要是黑碗放盘。本轮新增奶酪包入碗、酒瓶放酒架、碗放炉面、中层抽屉开合，涉及不同物体外形、接收区域和关节操作。固定plate/cookie接口已改为从原生库存生成可移动物品、区域和关节读数；不存在那两种物体也能运行。</p><p>人偏好取用的物品由背景给定：接收碗/酒瓶、奶酪包/盘或酒瓶/盘；偏好是人自己的信息，不是动作、目的地或时间清单。是否操作、换目标、请求空间或等待由真实Qwen决定。固定柜/炉/架只可观察或协商，不能当作可自由抓走的物品。</p><p>设置：libero_goal任务6/9/1/0、init0/seed0、independent倾向、episode记忆；每场景40s/20Hz，Qwen3-14B每2s选择，π0.5外/腕相机+8维本体，最多10步块。人用真实双指受力抓放，世界/策略各初始化一次，推理期间模拟时钟暂停。人的几何/关节读数是理想感知，机器人只读实际相机/自身状态和公开人话语。</p><p class="notice">无人物参照4/4完成基础操作，但它们首次成功后结束；伙伴条件同时改变人物、区域标记、语言和运行长度，且模型采样状态未配对。结果不能单独归因为Dynamic Human Policy、人格或算法HRC缺陷。接触手/身体仍是代理，完整统计和真人效度未验证。</p></section>
<section><h2>任务如何验收</h2><p>奶酪入碗保留原生On定义；酒瓶/炉面目标区域解析到其真实parent实体。放置需原生目标成立、接收面实际接触、机械臂与人手都释放并稳定0.2s。抽屉使用原生Open、关节变化超过0.02m、速度低于0.08m/s稳定0.2s，不套放置分数。个人整理也需实际桌面支撑与松手，不能仅凭接近目标判断完成。</p></section>
<section><h2>本批结果</h2><div class="scroll"><table><tr><th>任务</th><th>基础操作完成</th><th>伙伴下首次任务成立</th><th>机器人期末</th><th>人期末目标</th><th>人目标变化</th></tr>{''.join(table)}</table></div><ul>{''.join(findings)}</ul><p>已完成和最终维持分开，运动/显示资格与任务谓词分开。无可测个人目标不计作人任务失败，公开提案不等于机器人接受或双方理解。</p></section>
<section><h2>值得注意的实际行为</h2><p>酒瓶放架场景中，机器人在3.05秒双指接触并抬起的是奶酪包，而它公开任务的目标是酒瓶；人当时说自己要抓奶酪。奶酪包的11.65cm抬升不能误记为人已抓住，人的双指抬起见证始终没有出现。</p><p>这与把他人的自述当作自己的动作目标的解释相容，但还没有匹配视觉/运行长度/采样噪声的控制，不能证明语言是唯一原因。<a href="../../results/continuous_v2/scene_catalog_human/object_role_verification.json">按操作者和物品的实际接触见证</a>。</p><p>奶酪入碗场景的人抓的是机器人也要处理的奶酪，并将固定bowl_home区域当作容器目标；低层区域高度/语义不等于相对容器放置。盘和酒瓶等人的操作也没有校准出可靠抓放。失败包含人模型选择、低层能力和输入适配混杂，不能全归为机器人HRC缺陷。</p></section>{''.join(panels)}<section><h2>基础操作的前提证据</h2><p>以下真实π操作参照分别4.9s、7.0s、4.8s、6.8s完成，输入/原始动作/控制/时间轴和物理条件独立重建。仅用于确认模型接入和任务操作可用，不为人的任务或组合协作提供教师。</p></section>{''.join(refs)}
<section><h2>数据与下一步范围</h2><p>每条保留原始失败、物理世界状态、模型输入输出、公开话语、接触、关节和完整视频。按同stem组织真实模型观测/实际动作，失败不是专家示范。站姿人体不支持地面物体拾取，本批没有将地面任务偷偷抬到桌面；完整身体、更多房间/任务/模型/人格以及动态协商仍待推进。</p><p><a href="evidence.json">原始结果及来源</a> · <a href="README.md">完整设置与边界</a> · <a href="../articulated_hrc_20261007/index.html">上一批高台真实抓放</a></p></section></main>
<script>const runs={data};document.querySelectorAll('video[data-case]').forEach(v=>{{const target=document.getElementById('audit-'+v.dataset.case),run=runs[v.dataset.case];function update(){{let d=run.decisions[0];for(const r of run.decisions)if(r.time_s<=v.currentTime)d=r;target.textContent=`人模型 ${{d.time_s.toFixed(2)}}s · ${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n自己的目标：${{JSON.stringify(d.personal.personal_targets)}}\n长期意图：${{d.personal.long_term_intention}}\n说：${{d.decision.message}}\n理由：${{d.decision.reason}}\n运动阶段：${{d.measured.motor_phase}}；双指接触：${{JSON.stringify(d.measured.measured_finger_target_contacts)}}；测得在手：${{d.measured.object_measured_in_hand||'无'}}\n接口/运动反馈：${{d.measured.motor_failure||'无异常反馈'}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'object_role_audit':object_roles,'runs':evidence,'source_sha256':hashes},ensure_ascii=False,indent=2))
    print(HERE/'index.html')


if __name__=='__main__':main()
