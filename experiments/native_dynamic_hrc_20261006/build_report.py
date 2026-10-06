"""根据已完成的原生模型实测重建中文视频报告，不修改实验结果。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
RUNS=[('pi05_libero_native_reference','机器人原生操作参照'),
      ('native_human_presence_reference','有人体的静态场景参照'),
      ('native_qwen_moving_plate','早期生成式运行：持续观察停滞'),
      ('native_qwen_grounded_activity','原生动作与工作目标校准后的联合运行')]


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def href(path):return '../../'+path.relative_to(ROOT).as_posix()
def link(path,label):return f'<a href="{href(path)}">{escape(label)}</a>'


def main():
    sources,panels,tables,evidence=[],[],[],{}
    hero=''
    for name,label in RUNS:
        root=RESULTS/name
        required=['summary.json','provenance.json','video_verification.json','model_execution_verification.json']
        if not all((root/p).exists() for p in required):
            tables.append(f'<tr><td>{label}</td><td colspan="4">完整运行与核验尚未完成，不发布成绩。</td></tr>')
            continue
        assert read(root/'video_verification.json')['status']=='verified'
        verification=read(root/'model_execution_verification.json')
        assert verification['status']=='verified'
        summary=read(root/'summary.json')
        provenance=read(root/'provenance.json')
        source_changes=provenance['source_files_changed_during_run']
        assert not source_changes
        eligible={Path(row['episode']).resolve():row['motion_eligible'] for row in verification['episodes']}
        robot=human=joint=0
        episode_evidence=[]
        for metric in summary['episodes']:
            directory=root/f'task_{metric["task_id"]:02d}'/f'init_{metric["init_state_id"]:03d}'
            valid=eligible[directory.resolve()]
            robot+=bool(metric.get('robot_goal_success',metric['task_success'])) and valid
            human+=bool(metric.get('human_goal_success',False)) and valid
            joint+=bool(metric['task_success']) and valid
            decisions=rows(directory/'human_policy_io.jsonl') if (directory/'human_policy_io.jsonl').exists() else []
            intent=Counter(row['parsed_decision']['intent'] for row in decisions)
            errors=sum(bool(row.get('parse_error')) for row in decisions)
            detail=''
            if decisions:
                samples=[decisions[0],decisions[len(decisions)//2],decisions[-1]]
                examples=''.join(f'<li>{row["time_s"]:.1f}秒：{escape(row["parsed_decision"]["intent"])}。{escape(row["parsed_decision"]["reason"])}</li>' for row in samples)
                detail=f'<p>人实际生成{len(decisions)}次决定：{escape("、".join(f"{key} {count}次" for key,count in intent.items()))}，解析错误{errors}次。接触证据：{"有" if metric["human_contact_witness"] else "无"}；指尖峰值{metric["human_fingertip_peak_speed_m_s"]:.3f}m/s。</p><details><summary>实际决定与理由</summary><ul>{examples}</ul></details>'
                sources.append(directory/'human_policy_io.jsonl')
            physical_path=directory/'physical_operation_evidence.json'
            if physical_path.exists():
                physical=read(physical_path)
                detail+=f'<p>接触记录确认机器人双指夹持过碗，最大抬升{physical["maximum_bowl_lift_from_initial_m"]*100:.1f}cm；末帧夹爪打开且无机器人手指接触。这条包含实际拿起、移动和释放。{link(physical_path,"物理操作证据")}</p>'
                sources.append(physical_path)
            diagnosis_path=directory/'human_motion_diagnosis.json'
            if diagnosis_path.exists():
                detail+=f'<p>失败运行的超速窗口另行保存，发生机制尚未分离，不改动资格阈值。{link(diagnosis_path,"逐物理步诊断")}</p>'
                sources.append(diagnosis_path)
            outcomes=(f'机器人放碗：{"完成" if metric.get("robot_goal_success",metric["task_success"]) else "未完成"}'
                      + (f'；人的移盘：{"完成" if metric["human_goal_success"] else "未完成"}；共同任务：{"完成" if metric["task_success"] else "未完成"}' if decisions else ''))
            panel=f'''<article><h3>{label} · 场景{metric['task_id']+1}</h3><p>{outcomes}。运动资格：{"通过" if valid else "不合格，仅诊断"}；模拟{metric['completion_time_s']:.2f}秒，π0.5真实推理{metric['model_calls']}次。</p>
<video controls preload="metadata" poster="{href(directory/'preview.png')}" src="{href(directory/'demo.mp4')}"></video>{detail}<p>{link(directory/'metrics.json','原始结果')} · {link(root/'index.html','整批运行')} · {link(root/'model_execution_verification.json','独立执行核查')}</p></article>'''
            if decisions and valid and metric['task_success']:hero+=panel
            else:panels.append(panel)
            episode_evidence.append({**metric,'motion_eligible':valid,'human_intent_counts':dict(intent),'human_parse_errors':errors})
            sources.append(directory/'metrics.json')
        count=len(summary['episodes'])
        human_text=f'{human}/{count}' if provenance.get('human_mode')=='qwen' else '不设人类工作成绩'
        shared_text=f'{joint}/{count}' if provenance.get('human_mode')=='qwen' else '仅基础操作'
        tables.append(f'<tr><td>{label}</td><td>{robot}/{count}</td><td>{human_text}</td><td>{shared_text}</td><td>{verification["motion_eligible_episode_count"]}/{count}</td></tr>')
        sources.extend(root/p for p in required)
        evidence[name]={'episodes':episode_evidence,'settings':provenance,'verification':verification}
    stamp={'status':'execution_evidence','research_goal_achieved':False,'runs':evidence,
           'source_sha256':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sources},
           'interpretation':'直接报告执行与失败，不以小样本原生成功、生成式输出或代理身体证明完整HRC能力。'}
    (HERE/'evidence.json').write_text(json.dumps(stamp,ensure_ascii=False,indent=2))
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真实模型与动态接收盘 · HRC系统报告</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f4;color:#193540;font:17px/1.85 system-ui;overflow-wrap:anywhere}}main{{max-width:1100px;margin:auto;padding:28px 20px}}header{{background:#173f48;color:white;padding:30px;border-radius:16px}}section,article{{background:white;padding:26px;border-radius:14px;margin:24px 0}}h1{{font-size:clamp(26px,4vw,38px);line-height:1.4}}h2{{font-size:25px}}h3{{font-size:21px}}video{{width:100%;max-height:640px;background:#142430}}a{{color:#137a7b}}.notice{{background:#fff3e2;padding:18px;border-left:5px solid #b47731}}.table-wrap{{overflow:auto}}table{{min-width:760px;border-collapse:collapse;width:100%}}th,td{{padding:12px;border-bottom:1px solid #d2dfde;text-align:left}}li{{margin:8px 0}}@media(max-width:600px){{main{{padding:12px}}section,article,header{{padding:20px 16px}}}}
</style><main><header><h1>当人改变接收盘位置，真实具身模型如何继续操作？</h1><p>本轮先取得可完成抓放的π0.5-LIBERO原生参照，再让Qwen生成式伙伴参与同一物理世界。视频直接来自运行时Sim相机；动作和贡献以实际记录为准。下方先展示通过核查的共同完成。</p></header>{hero}
<section><h2>为什么改变实验路径</h2><p>此前Genesis域的关节位置适配完成了3000步训练，但独立操作0/6；继续比较协作会混入基础操作失效。
现有中国源仿真预训练权重改接配套LIBERO原生环境，保持两路相机、8维末端状态和7维操作空间动作，已取得三个任务的实际成功。
这说明项目有了可工作的学习模型参照；环境、相机与控制同时改变，不能说已证明单一修改的因果效果。</p>
<p>已有Genesis/VC实验继续保留：{link(ROOT/'experiments/dynamic_contact_20261006/index.html','上一阶段完整报告与18段视频')}。</p></section>
<section><h2>这次共同任务怎样运行</h2><p>桌上有两个黑碗、盘子、瓷碗、饼干和厨房设施。三项原生任务分别要求把盘子与瓷碗之间、靠近瓷碗、桌面中央的指定黑碗放到盘子上。这是同一取放技能的三个摆放关系，不是三种独立HRC任务族。</p>
<p>人的公开目标是把盘子移近自己，盘子中心需到达绿色圆点附近。机械臂继续放碗；接收盘的位置、占用与接触会随人的行动变化。
双方没有预先固定的执行顺序：Qwen根据公开坐标、手状态、对话和自身经历选择推、观察或清离；π0.5根据实际双相机、末端状态和公开语言输出动作。</p>
<p>物理20Hz控制，机器人每10步重新推理；人约每秒决定一次。推盘的接近、下降、受力推进是低层运动原语；人的行动目标与时机由真实语言模型决定，机器人没有教师接管。
人的公开坐标是理想化感知，机器人使用相机；人的指尖由限幅力驱动，盘子不吸附、不写控制期坐标。人体外观是非碰撞运动学代理。</p>
<p>共同任务需同时满足原生放碗关系和人的移盘条件。移盘还需实际指尖接触、接近原支撑高度、速度低于0.08m/s持续0.2秒；位移/高度容差为25mm。
运动资格另检查指尖与物体速度；不合格片段保留视频，不进入合格汇总。不使用未经校准的加权cobalance总分。</p></section>
<section><h2>已完成结果</h2><div class="table-wrap"><table><thead><tr><th>运行条件</th><th>机器人工作</th><th>人的工作</th><th>共同任务</th><th>运动合格</th></tr></thead><tbody>{''.join(tables)}</tbody></table></div>
<p>上表只计运动合格的完成，分母保留预定场景数。新联合运行原始结果为机器人2/3、人2/3、共同1/3；其中场景2指尖峰值2.446m/s超过0.65m/s门槛，仅保留诊断，不计人的有效完成。共同成功的场景3通过运动门槛。</p>
<p>各条件都有完整视频、像素和动作链路核查。只有同一初始状态、合作型persona和小样本；不同批次模型采样没有严格重置配对，不能用这些比例宣称显著效果或人格因果。</p>
<div class="notice">早期Qwen连续选择观察，虽然已提供当前坐标仍反复要求确认。后续将人类接口改为原生支持的动作，并明确较长期工作目标与当前观察动作的区别；这是接口/代理校准，不能称为记忆效用或协作能力提升的消融。</div></section>
{''.join(panels)}
<section><h2>当前边界与接下来的研究</h2><p>目前已具备真实机器人模型、生成式人类策略、共享物体的接触变化与可审计视频链路，但尚未完成成熟Benchmark。
当前主要是一种接收盘变化任务，只有合作型伙伴和一个机器人模型；人体是简化外观及指尖代理，没有全身运动、走动抓持或真人行为效度。推理期间模拟时间暂停，现实异步延迟也未测。</p>
<p>扩展方向是更多任务关系、不同人物偏好与意图变化、不同现成算法、持续世界任务流、运动/接触资格以及人的负担与双方贡献的独立指标。结果应让基础操作失败、代理停滞和真实协调失败能够分别定位。</p>
<p>方法来源：<a href="https://github.com/Physical-Intelligence/openpi/tree/main/examples/libero">官方OpenPI原生LIBERO评测</a> · <a href="https://github.com/dannymcy/coopera_code/blob/main/HUMAN.md">COOPERA人类模拟</a>。借用人格、持续意图和经历组织原则，不将合成代理当成真人。</p></section></main></html>'''
    (HERE/'index.html').write_text(page)
    print(HERE/'index.html')


if __name__=='__main__':main()
