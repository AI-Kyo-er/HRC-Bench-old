"""从已完成的实际接触运行和示范数据重建报告，不运行模型或改写评分。"""
from collections import Counter
from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESULTS = ROOT / 'results/continuous_v2'
CANDIDATES = ('pi05_lora_qwen_memory_contact', 'pi05_qwen_feedback_contact', 'pi05_qwen_articulated_contact')
NAMES = {'relay': '接力', 'concurrent_overlay': '并行作业', 'robot_induced_rebalance': '进度受阻与重新协调'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def href(path):
    return '../../' + path.relative_to(ROOT).as_posix()


def link(path, label):
    return f'<a href="{escape(href(path))}">{escape(label)}</a>'


def video(directory):
    return f'<video controls preload="metadata" poster="{href(directory / "preview.png")}" src="{href(directory / "demo.mp4")}"></video>'


def finished_run(directory):
    required = ('summary.json', 'provenance.json', 'index.html',
                'video_verification.json', 'model_execution_verification.json')
    return (all((directory / name).is_file() for name in required)
            and read(directory / 'video_verification.json')['status'] == 'verified'
            and read(directory / 'model_execution_verification.json')['status'] == 'verified')


def adaptation_panel():
    training = ROOT / 'results/contact_training/pi05_lora_v1'
    evaluation = RESULTS / 'pi05_lora_atom_evaluation'
    if not (training / 'summary.json').exists():
        return '', {}, []
    summary, provenance = read(training / 'summary.json'), read(training / 'provenance.json')
    curve = [row for row in rows(training / 'training.jsonl') if 'dev_loss' in row]
    maximum = max(row['dev_loss'] for row in curve)
    points = ' '.join(f"{45 + row['step'] / summary['steps'] * 620:.1f},{200 - row['dev_loss'] / maximum * 160:.1f}" for row in curve)
    plot = f'''<svg viewBox="0 0 710 240" role="img" aria-label="固定验证样本上的损失随训练步数下降" style="width:100%;max-width:710px">
<path d="M45 30 V200 H680" fill="none" stroke="#536879"/><polyline points="{points}" fill="none" stroke="#126b70" stroke-width="3"/>
<text x="45" y="225">0 步</text><text x="620" y="225">{summary['steps']} 步</text>
<text x="50" y="25">{summary['initial_dev_loss']:.3f}</text><text x="585" y="185">{summary['final_dev_loss']:.3f}</text></svg>'''
    sources = [training / name for name in ('summary.json', 'provenance.json', 'training.jsonl')]
    evaluation_evidence, panels = [], []
    if finished_run(evaluation):
        verified = read(evaluation / 'video_verification.json')
        assert verified['status'] == 'verified'
        for metric in read(evaluation / 'summary.json')['episodes']:
            directory = evaluation / metric['scenario']
            physics = read(directory / 'physics_contract.json')
            evaluation_evidence.append({key: metric[key] for key in ('scenario', 'seed', 'task_success', 'completed_skills')})
            panels.append(f'''<article><h3>{escape(metric['scenario'])} · 基础操作</h3>
<p>同一个适配后模型、seed {metric['seed']}、30 秒、每 tick 重新推理；伙伴只观察。真实接触抬起记录 {len(physics['contact_grasp_objects'])} 个对象，
合法贡献 {len(metric['completed_skills'])} 项，任务{'完成' if metric['task_success'] else '未完成'}。该测试检查基本操作，不能解释成人机协作成绩。</p>
{video(directory)}<p>{link(directory / 'metrics.json', '原始成绩')} · {link(directory / 'physics_contract.json', '接触与贡献证据')}</p></article>''')
            sources += [directory / 'metrics.json', directory / 'physics_contract.json']
        sources += [evaluation / name for name in ('summary.json', 'provenance.json', 'video_verification.json', 'model_execution_verification.json')]
    done = sum(row['task_success'] for row in evaluation_evidence)
    outcome = (f'独立闭环基本操作完成 {done}/{len(evaluation_evidence)}。'
               if evaluation_evidence else '独立闭环评测尚未完成，不发布模型操作结论。')
    document = f'''<section><h2>本轮实际训练，以及训练后能否操作</h2>
<p>针对当前 Sim 操作分布，从已有 π0.5-DROID 权重进行 {summary['steps']} 步 LoRA 训练，仅更新 {provenance['trainable_parameters']:,} 个适配参数。
使用官方 OpenPI 训练步骤和原有 DROID 归一化；完整动作块的候选训练样本 {provenance['train_samples']} 个、验证样本 {provenance['dev_samples']} 个，batch size {provenance['batch_size']}。
只使用本地权重和已经生成的实际接触示范，没有下载新模型。</p>
<p>曲线是在固定 16 个验证样本、固定噪声上计算的 flow-matching loss，从 {summary['initial_dev_loss']:.3f} 降到 {summary['final_dev_loss']:.3f}。
它衡量对示范监督的拟合，不等于抓取成功率，也不是全部验证集上的泛化成绩。
当前有效 dev 只含红、蓝示范；绿色仅有一条成功训练示范，没有有效 dev 操作。时间相邻的动作窗口也不能视为独立试验。</p>{plot}
<div class="notice">{outcome} 所以模型适配与闭环有效性必须分别报告；当前数据量与操作覆盖仍小，不能据此排名先进模型的 HRC 能力。
这轮提示、动作块执行长度与早先原生模型运行不同，也不是严格配对的前后提升实验。</div>
<p>{link(training / 'summary.json', '训练结果')} · {link(training / 'provenance.json', '训练设置与来源')} · {link(training / 'training.jsonl', '逐步训练记录')}</p>
{''.join(panels)}</section>'''
    return document, {'training': summary, 'settings': provenance, 'atomic_evaluation': evaluation_evidence}, sources


def main():
    native = next(RESULTS / name for name in CANDIDATES if finished_run(RESULTS / name))
    provenance = read(native / 'provenance.json')
    summary = read(native / 'summary.json')
    robot_label = 'π0.5-DROID（本轮 LoRA 适配权重）' if provenance['model_server_metadata'].get('contact_lora') else 'π0.5-DROID（官方原生权重）'
    adaptation, adaptation_evidence, adaptation_sources = adaptation_panel()
    table, panels, evidence, source_paths = [], [], [], [native / 'summary.json', native / 'provenance.json', native / 'video_verification.json']
    decision_count = 0
    memory_records = []
    robot_total = human_total = success_count = 0
    for metric in summary['episodes']:
        matches = [path.parent for path in native.rglob('metrics.json')
                   if read(path).get('scenario') == metric['scenario'] and read(path).get('seed') == metric['seed']]
        assert len(matches) == 1
        directory = matches[0]
        motion = read(directory / 'motion_verification.json')
        physics = read(directory / 'physics_contract.json')
        policy = rows(directory / 'human_policy_io.jsonl')
        decisions = [row['parsed_decision'] for row in policy]
        goals = [(row.get('object_id'), row.get('destination')) for row in decisions if row.get('object_id')]
        target_changes = sum(a != b for a, b in zip(goals, goals[1:]))
        memory_path = directory / 'human_memory.jsonl'
        if memory_path.exists():
            memory_records.extend(rows(memory_path))
            source_paths += [memory_path, directory / 'human_policy_io.jsonl']
        calls = next(row['model_calls'] for row in provenance['episode_model_calls']
                     if row['scenario'] == metric['scenario'] and row['seed'] == metric['seed'])
        robot = [skill for skill in metric['completed_skills'] if skill.startswith('robot:')]
        human = [skill for skill in metric['completed_skills'] if skill.startswith('human:')]
        contact_rows = rows(directory / 'contacts.jsonl')
        alignment = max(row['human_hand_alignment']['distance_m'] for row in contact_rows if 'human_hand_alignment' in row)
        title = f"{NAMES[metric['scenario']]} · seed {metric['seed']}"
        success_count += bool(metric['task_success'])
        robot_total += len(robot)
        human_total += len(human)
        decision_count += len(policy)
        intents = Counter(row['intent'] for row in decisions)
        parse_errors = sum(bool(row.get('parse_error')) for row in policy)
        snippets = ''.join(f"<li>{record['time_s']:.1f} 秒：{escape(record['parsed_decision']['intent'])} / {escape(str(record['parsed_decision'].get('object_id')))}。{escape(record['parsed_decision'].get('reason', ''))}</li>"
                           for record in (policy[0], policy[len(policy) // 2], policy[-1]))
        table.append(f'<tr><td>{title}</td><td>{"通过" if metric["task_success"] else "未完成"}</td>'
                     f'<td>{len(robot)} / {len(human)}</td><td>{calls} / {len(policy)}</td>'
                     f'<td>{motion["status"]}</td><td>{alignment * 1000:.1f} mm</td></tr>')
        panels.append(f'''<article><h3>{title}</h3><p>原始活动终态：{"通过" if metric['task_success'] else "未完成"}。
机器人合法贡献 {len(robot)} 项，人合法贡献 {len(human)} 项。Qwen 生成了 {len(policy)} 次决定，目标对象/目的地改变 {target_changes} 次；
实际意图包括 {escape('、'.join(f'{key} {value} 次' for key, value in intents.items()))}；输出解析失败 {parse_errors} 次。
人的实物抓取涉及 {len(physics['human_contact_grasp_objects'])} 个物体，机器人涉及 {len(physics['contact_grasp_objects'])} 个。</p>
{video(directory)}<p>持握/释放过程中物体最大单物理帧位移 {motion['maximum_human_object_displacement_per_physics_step_m'] * 1000:.1f} mm；
显示手腕与物理手最大距离 {alignment * 1000:.1f} mm。运动核验只检查这一项，不等于完整研究效度。</p>
<p>{link(native / 'index.html', '逐事件报告与双相机输入')} · {link(directory / 'human_policy_io.jsonl', '生成式伙伴实际决定')}
 · {link(directory / 'policy_io.jsonl', '真实机器人模型动作')} · {link(directory / 'motion_verification.json', '运动核验')}</p>
<details><summary>伙伴实际决定摘录</summary><ul>{snippets}</ul></details></article>''')
        evidence.append({'scenario': metric['scenario'], 'seed': metric['seed'], 'activity_success': metric['task_success'],
                         'robot_contributions': robot, 'human_contributions': human, 'model_calls': calls,
                         'human_decisions': len(policy), 'target_changes': target_changes,
                         'human_parse_errors': parse_errors,
                         'maximum_wrist_alignment_error_m': alignment, 'motion_status': motion['status'],
                         'interpretation': '执行器与模型整体运行，不从任务失败直接推断 HRC 能力。'})
        source_paths += [directory / 'metrics.json', directory / 'motion_verification.json', directory / 'physics_contract.json']
    calibration = RESULTS / 'human_contact_formal'
    cal_episode = calibration / 'human_contact_calibration'
    cal_metric = read(cal_episode / 'metrics.json')
    cal_motion = read(cal_episode / 'motion_verification.json')
    datasets, dataset_tables, sample_panels = [], [], []
    frame_total = demo_success = demo_total = 0
    for name in ('contact_demonstrations_v1', 'contact_feedback_demonstrations'):
        dataset_root = ROOT / 'datasets' / name
        if not (dataset_root / 'dataset.json').exists():
            continue
        metadata = read(dataset_root / 'dataset.json')
        datasets.append({'name': name, 'metadata': metadata})
        source_paths += [dataset_root / 'dataset.json', dataset_root / 'provenance.json', dataset_root / 'video_verification.json']
        for exported in metadata['exports']:
            demo_total += 1
            demo_success += bool(exported['exported_frames'])
            frame_total += exported['exported_frames']
        dataset_tables.append(f'<tr><td>{name}</td><td>{sum(bool(row["exported_frames"]) for row in metadata["exports"])} / {len(metadata["exports"])}</td>'
                              f'<td>{metadata["verified_samples"]["train"]}</td><td>{metadata["verified_samples"]["dev"]}</td>'
                              f'<td>{link(dataset_root / "index.html", "实际示范与视频")}</td></tr>')
        successful = [row for row in metadata['exports'] if row['exported_frames']]
        if successful:
            selected = successful[0]
            sample_panels.append(f'<article><h3>真实示范：{escape(selected["episode"])}</h3><p>几何教师通过关节控制完成物理操作；此处展示数据生成，不是训练模型成绩。</p>{video(dataset_root / selected["episode"])}</article>')
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    count = len(summary['episodes'])
    memory_section = ''
    if memory_records:
        unique = list({record['text']: record for record in reversed(memory_records)}.values())
        unique.sort(key=lambda record: record['time_s'])
        examples = ''.join(f"<li>{record['time_s']:.1f} 秒：{escape(record['text'])}</li>" for record in unique[:4])
        memory_section = f'''<section><h2>伙伴怎样根据经历改变下一步</h2><p>这轮 Qwen 在每次决定时看到当前公开状态、最近 10 次带时间的观察、最近 4 次公开决定和最近 12 条自身生成的经验。
它输出行动、解释与可选记忆，实际写入 {len(memory_records)} 条经验。以下是实际模型输出，可能有判断错误，不是评测器认证的事实。</p><ul>{examples}</ul>
<p>这些是生成的经验文本，而非手工信任分数或固定路由表；动作执行器仍使用阶段控制把意图变成连续物理动作。
记忆当前只在单个 episode 内保留，尚未验证跨活动记忆或真人行为效度，也未用消融证明记忆改善了协作。</p>
<div class="notice">本轮接力运行中，伙伴整段围绕蓝块观察、接近和持握，没有完成自己原先承诺的红块前置贡献；后期还把蓝块称为自己的任务。
其最后一次输入的最近 16 条公开对话已经不含初始红块分工。这暴露了任务理解与记忆组织的边界；不能据此声称发现了真实人类的行为规律，也不能仅凭这次运行确定因果。</div></section>'''
    source_paths += adaptation_sources
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>动态人类与真实接触 HRC · 实际系统报告</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f4;color:#182e3e;font-family:system-ui,"Noto Sans CJK SC",sans-serif;line-height:1.8;overflow-wrap:anywhere}}
main{{max-width:1100px;margin:auto;padding:32px 24px 70px}}header{{padding:32px;border-radius:18px;background:#143842;color:white}}
h1{{font-size:clamp(25px,4vw,39px);line-height:1.4;margin:12px 0 20px}}h2{{margin:0 0 12px;font-size:24px}}h3{{font-size:20px}}
.eyebrow{{color:#a5dbca;letter-spacing:1px;font-size:14px}}section{{padding:28px;background:white;border-radius:16px;margin:24px 0}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.stat{{background:#e2eeeb;border-radius:12px;padding:18px}}
.stat strong{{display:block;font-size:28px}}.stat span{{font-size:14px;color:#536879}}a{{color:#126b70;text-underline-offset:3px}}
.notice{{background:#fff4e5;border-left:5px solid #bd7928;padding:18px 22px;margin:20px 0}}article{{padding-top:12px;border-top:1px solid #d5e2e1;margin:26px 0}}
video{{width:100%;max-height:720px;background:#142430;border-radius:12px}}.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;min-width:760px;width:100%;font-size:14px}}
th,td{{padding:12px;border-bottom:1px solid #d8e3e1;text-align:left;vertical-align:top}}th{{background:#eaf1ef}}.quiet{{font-size:14px;color:#586b7b}}
@media(max-width:650px){{main{{padding:16px 12px 40px}}header,section{{padding:20px 16px}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><main><header><div class="eyebrow">HRC CONTINUOUS · 真实模型、接触动作与实际示范数据</div>
<h1>动态伙伴在真实接触场景中，实际做了什么？</h1>
<p>本页最新联合运行使用 {robot_label} 与 Qwen3-14B 合成伙伴。两者的动作在同一物理时间轴中执行，物体通过接触移动；视频直接来自运行时相机。
下方分别呈现真实模型结果、接触手校准与可用于模型校准的数据。</p></header>
<div class="stats"><div class="stat"><strong>{count} 条</strong><span>本次实际模型运行</span></div>
<div class="stat"><strong>{provenance['model_calls']} 次</strong><span>π0.5 实际推理</span></div><div class="stat"><strong>{decision_count} 次</strong><span>Qwen 意图决定</span></div>
<div class="stat"><strong>{frame_total} 帧</strong><span>真实接触示范监督</span></div></div>
<section><h2>目的与设置</h2><p>实验要观察：当人的行动由生成式模型根据可见进度决定、机械臂由训练后的具身模型控制时，双方能否完成共同活动，人的目标选择怎样影响实际过程。
模型能力判断需要基本操作可用、人的动作连续、任务评分按实际贡献区分。</p>
<p>本次运行后端为 Genesis，机器人 15 Hz 控制，最长 60 秒模拟时间；人体意图约每秒更新一次，物理推进为 60 Hz。
π0.5 只接收实际外部/腕部相机、本体状态与公开任务语言。Qwen 读取公开几何、公开对话、自身动作状态与近期公开决定，输出目标对象、目的地、行动意图、速度和公开表达。</p>
<p>本批基础操作指令使用英文，运行对话使用中文，尚未做语言条件对照。机器人的初始操作指令也没有完整保留串行任务的公开前置说明；因此本批不用于判断模型能否正确理解和遵守这些协调约定。
运行结束后已修订输入去重，只去除初始的普通搬运句，保留附加公开约束；该修订通过回归测试，本页视频和模型成绩仍是修订前执行的结果。</p>
<p>初始分工与活动依赖构成任务契约；执行中双方动作、占用、碰撞和未完成会改变后续观察。本次只使用 cooperative 伙伴，尚未形成不同人格与多模型的正式比较。
机械臂直接执行模型给出的关节动作，不由几何教师接管。每次推理产生 15 步动作，本批最多执行 {provenance['execution_horizon']} 步后重新观察；公开纠正或失败反馈会提前丢弃旧动作块。</p>
<h3>三项联合任务具体做什么</h3><div class="table-wrap"><table><thead><tr><th>任务</th><th>初始公开分工</th><th>协调要求与完成条件</th></tr></thead><tbody>
<tr><td>接力</td><td>人整理红块，机器人整理蓝块，分别放到指定收纳区。</td><td>红块贡献提交后，蓝块操作才能获得有效贡献；两项都完成才算共同活动完成。</td></tr>
<tr><td>并行作业</td><td>人把蓝块放到留用区；机器人把红、绿块放到收纳区。</td><td>允许并行。双方面对同一工作台的空间占用，三项都要稳定释放并提交贡献。</td></tr>
<tr><td>进度受阻与重新协调</td><td>人先整理蓝块；机器人整理红、绿块。</td><td>机器人两项以前置蓝块贡献为条件。伙伴可根据可见停顿重新表达意图或接管；是否真的发生，由实际记录回答。</td></tr>
</tbody></table></div>
<p>桌面物体是自由刚体收纳块，旧任务名称中的“杯”沿用于历史定义。蓝色底板为收纳区，绿色底板为留用区。
本轮原生关节控制没有套用语义搬运基线的人工失败/延迟注入；受阻来自实际模型与物理执行，不能把继承的场景参数当成已发生的扰动。</p>
<h3>一次实验如何运行和评分</h3><p>每个 episode 只在开始时初始化布局与公开分工，随后人和机械臂共享同一物理世界。
每个 1/15 秒，机器人读取双相机与本体状态并提交底层动作；伙伴在更新时读取公开位置、对话与自己的经历，选择意图。
仿真器推进接触、重力和碰撞，再把实际新状态交给双方。Qwen 当前使用结构化几何观察，还没有视觉感知误差模型。</p>
<p>评分只接受有实际接触抬起证据、在目标区域稳定释放至少 0.4 秒、且操作当时满足前置条件的贡献。人的接管可完成活动，却不会算作机器人的贡献。
到截止时刻冻结成绩；其后 1.5 秒只录制物理稳定过程。记录同时保留行动原始输出、公开观察、接触、贡献与视频时间轴。</p></section>
<section><h2>人的动作现在怎样执行</h2><p>Qwen 选择做什么；接触手以关节受力完成伸手、夹持、抬起和释放。显示人物使用已有步行动作与躯干 IK，跟随实际物理手的位置。
人的物体拿放不再调用 Avatar 对物体坐标的直接写入，也没有把物体绑定到机械臂。</p>
<p>独立几何教师完成蓝块抓放用时 {cal_metric['completion_time_s']:.1f} 秒；持握/释放时最大单物理帧位移 {cal_motion['maximum_human_object_displacement_per_physics_step_m'] * 1000:.1f} mm，运动核验通过。
该校准检查执行器，不是 Qwen 或 π0.5 的能力结果。</p>{video(cal_episode)}
<p>{link(calibration / 'index.html', '接触手校准报告')} · {link(cal_episode / 'contacts.jsonl', '实际接触记录')}</p>
<div class="notice">接触手是简化关节代理，显示身体为动作数据与 IK，碰撞体为粗略代理。它尚不等于完整人体动力学或灵巧手，也未经真人行为校准。
模型推理期间模拟时钟暂停，本轮没有测量推理延迟对正在活动的人产生的影响。</div></section>
<section><h2>实际模型结果与贡献归属</h2><div class="table-wrap"><table><thead><tr><th>任务</th><th>共同活动终态</th><th>机器人 / 人合法贡献</th><th>π0.5 / Qwen 调用</th><th>运动核验</th><th>最大手腕对齐误差</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>本次共同活动通过 {success_count}/{count}；机器人实际合法贡献 {robot_total} 项，人贡献 {human_total} 项。
贡献要求实际接触操作与稳定释放；人的接管完成不会被统计成机器人贡献。</p>
<div class="notice">这些结果仍不足以排名模型的 HRC 或 cobalance 能力。π0.5 在当前操作分布中尚未建立有效基础操作表现；人的意图改变与动作执行之间也有失败边界。
任务未完成不能直接归因为“模型不会协作”。本页不使用手工加权总分掩盖这些问题。</div>
{''.join(panels)}</section>
{adaptation}
{memory_section}
<section><h2>用于后续模型校准的实际示范 Dataset</h2><p>已采集 {demo_total} 条接触操作运行，{demo_success} 条形成有效示范，共 {frame_total} 个双相机/本体状态/动作监督样本。
目标来自实际下一物理步的关节变化，避免把大幅 IK 目标跳变当成已执行动作。失败运行保留视频与原始记录，不生成有效训练目标。</p>
<div class="table-wrap"><table><thead><tr><th>数据批次</th><th>有效示范 / 运行</th><th>train 样本</th><th>dev 样本</th><th>查看</th></tr></thead><tbody>{''.join(dataset_tables)}</tbody></table></div>
<p>红、蓝操作能够完成。最初的绿色示范显示物体被推离原始取物点、动作未重新定位；增加实际位置反馈后已有成功案例，仍有失败。
因此每类物体和布局需要通过真实操作检查，不能只凭 IK 接口或场景定义认定任务可用。</p>
<p>样本按输入文件 stem 匹配腕部图像、状态和目标，无配对 manifest。加载器输出 15×8 动作块并标出有效时段，已逐样本读取核查；上述 LoRA 训练只使用完整动作块，示范成绩不计入模型评测。</p>
{''.join(sample_panels)}</section>
<section><h2>已确认的进展与未完成项</h2><p>已实际运行：真实机械臂模型、生成式伙伴选择意图、受力接触拿放、人物显示对齐、多活动契约、图像动作监督和逐事件视频核查。
人体瞬时搬运已被连续接触操作替换；最新执行器还加入了物体位置反馈、腕部方向与释放退让队列。</p>
<p>仍缺少：经过校准的模型基础操作、多模型能力差异、稳健的动作恢复、动态人类长期记忆与开放目标、多人格/未见任务组合，以及完整人体物理与真人效度。
整体研究目标仍在进行。</p>
<h3>接下来优先完成</h3><ol><li>让每个任务的基本操作与动态物体恢复通过实测，清除执行器和场景带来的地板问题。</li>
<li>持续保留公开分工、承诺和依赖，验证生成式伙伴的任务理解与跨活动记忆；使用实际示范继续校准机器人的操作分布。</li>
<li>扩展到现有九类活动契约、开放目标与持续历史，加入不同生成式伙伴和更多真实具身算法。</li></ol></section>
<section><h2>原始证据与核查</h2><p>{link(native / 'video_verification.json', '本次真实视频核验')} · {link(native / 'provenance.json', '模型、控制设置与源码记录')}
 · {link(native / 'model_execution_verification.json', '模型像素与动作链路核查')}
 · {link(ROOT / 'experiments/goal_progress_20261005/index.html', '此前阶段报告')}</p>
<p>每条重要运行均保存真实 Sim 视频及逐帧时间轴；轨迹画布用于审计。不同执行器版本是工程诊断，不能累积成独立模型样本或当作严格配对的效果提升。</p>
<details><summary>数据、实现与复现边界</summary><p>模型和大型数据实际保存在数据盘，仓库通过软链接访问。本轮使用已有本地权重，没有下载新模型或数据集。
后续下载只允许中国大陆镜像或本土服务，不通过 VPN。</p><p>Dataset 的 train/dev 划分是示范检查范围，不是已验证的跨任务或跨人泛化。
Robot 模型只有 π0.5；Qwen 为合成伙伴。人的动作原语属于执行器，几何教师只用于校准与示范生成。</p>
<p>{link(ROOT / 'src/hrc_pilot/human_contact.py', '动作执行器')} · {link(ROOT / 'experiments/continuous_v2/physical_frame_dataset.py', '按 stem 加载的数据接口')}
 · {link(ROOT / 'scripts/collect_contact_demonstrations.py', '实际示范采集入口')}</p></details>
<p class="quiet">记录批次：{native.name}。生成时间：{stamp}。本页从保存结果重建，不重新评分。</p></section></main></body></html>'''
    (HERE / 'index.html').write_text(document, encoding='utf-8')
    (HERE / 'evidence.json').write_text(json.dumps({'generated_at': stamp, 'native_run': native.name,
        'episodes': evidence, 'demonstration_episodes': demo_total, 'valid_demonstration_episodes': demo_success,
        'valid_frame_samples': frame_total, 'goal_complete': False, 'research_validity': 'unverified',
        'model_adaptation': adaptation_evidence,
        'generated_human_memory_count': len(memory_records),
        'source_sha256': {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in source_paths},
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(HERE / 'index.html')


if __name__ == '__main__':
    main()
