"""生成已有实验的中文总报告；不运行实验，不修改来源结果。"""
from __future__ import annotations

import hashlib
import html
import json
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES: dict[str, str] = {}


def load(path: Path):
    raw = path.read_bytes()
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def link(path: str, label: str | None = None) -> str:
    if not (ROOT / path).exists():
        raise FileNotFoundError(path)
    return f'<a href="../../{quote(path)}">{html.escape(label or path)}</a>'


def runs(names: list[str], pilot: bool = False) -> str:
    base = 'results/pilot_v1/' if pilot else 'results/continuous_v2/'
    items = []
    for name in names:
        directory = ROOT / base / name
        report = directory / 'index.html'
        summary = next(directory / f for f in SUMMARY_FILES if (directory / f).exists())
        items.append('<li><code>' + html.escape(name) + '</code> · ' +
                     (link(str(report.relative_to(ROOT)), 'HTML 报告') + ' · ' if report.exists() else '') +
                     link(str(summary.relative_to(ROOT)), '原始汇总') + '</li>')
    return '<ul class="files">' + ''.join(items) + '</ul>'


SUMMARY_FILES = ['summary.json', 'paired_summary.json', 'history_counterfactual_summary.json']
STAGES = [
    dict(id='e01', title='早期 pilot：历史与当前信息是否会改变选择', kind='Genesis / 手写机器人',
         purpose='先验证你的想法能否落到可执行条件：当前桌面相似时，历史、后来更新的信息、伙伴是否可用，会不会改变机器人应该做的事。',
         setup='五个条件 history_keep、history_pack、information_update、partner_available、partner_unavailable；每个条件分别运行 memory、static、reactive 三个手写机器人策略，共 15 条。人的表现由规则脚本驱动；机器人走 IK/动作阶段；物品运动学吸附。',
         result='按当时终态评分，memory 5/5、static 3/5、reactive 4/5；15 条均保存真实 Genesis 视频。三者都读取最初指令/分工；memory 保留此前约定并响应纠正和拒绝，static 不据后续纠正/拒绝更新，reactive 在收到 moved 事件后将红杯意图重置为 pack，做局部恢复而丢失此前约定。',
         limit='这是机制和仿真底座验证。三种策略都是人编写的，不是三个具身模型，也不是现有模型能力等级。固定前导片段不能代替完整持续协作。',
         dirs=['formal'], pilot=True, code=['src/hrc_pilot/scenarios.py','src/hrc_pilot/policies.py','src/hrc_pilot/partner.py','src/hrc_pilot/evaluation.py']),
    dict(id='e02', title='连续运行时：让活动、分工和事件持续更新', kind='参考后端 / 手写策略',
         purpose='从单个选择题走向持续共同活动：工作有前置依赖，世界逐 tick 推进，延迟、失败、求助、接管、暂离与返回可以改变后续过程。',
         setup='建立 ActivityContract、工作项、交互结构与公开观察。GreedyPublicPolicy 根据可见任务和当前条件选动作；规则伙伴更新 trust、reliability、workload 等数值，再对候选行为打分。先在 ContinuousWorld 参考后端运行六个场景及生成场景。',
         result='formal/formal_v10 六场景各 6/6 通过该版本评分；生成器与运行器能保存情境、观察、动作、事件和指标。参考后端轨迹回放不是 Genesis 视频。',
         limit='这是程序逻辑验证。动态分工仍由手写规则实现，状态数值不是从真人行为学到的心理模型；机器人仍是透明基线。',
         dirs=['formal','formal_v4','formal_v5','formal_v6','formal_v10'], code=['src/hrc_pilot/continuous.py','scripts/run_continuous_benchmark.py']),
    dict(id='e03', title='结构与伙伴配对：区分任务完成和协作组织', kind='参考后端 / 三种伙伴',
         purpose='检查相同基础操作在孤立、顺序串接、组合和结构留出条件下是否都可执行，并比较不同伙伴响应机制。',
         setup='paired_v8 是四个结构条件 × fixed_replay/reactive/adaptive 三个伙伴，共 12 条；paired_v10 是六场景 × 三伙伴，共 18 条。机器人保持手写公共策略。fixed_replay 固定重放，reactive 按当前公开事件响应，adaptive 另外保留跨步骤状态并调整分工。',
         result='两个目录分别 12/12、18/18 完成。接口能组织配对条件与结构标签；这还没有建立先进模型在结构留出上的泛化分数。',
         limit='此处三种条件是“人类伙伴算法”，与 E01 的三个“机器人策略”不是同一分类。全部完成本身不能说明条件具有足够区分力。',
         dirs=['paired_v8','paired_v10'], code=['src/hrc_pilot/continuous.py','src/hrc_pilot/dataset.py']),
    dict(id='e04', title='连续场景迁入 Genesis：真正渲染场景与过程', kind='Genesis / 手写协作',
         purpose='验证参考运行时能在 VC/Genesis 中逐步执行，给出 RGB、关节轨迹和真实 Sim 视频，而不仅是二维事件动画。',
         setup='genesis_v10 六场景各一条；genesis_paired_v10 六场景 × 三伙伴 18 条。机器人语义动作由阶段控制和 IK 执行，Avatar 由动作接口驱动，物品仍吸附/自动放置。',
         result='分别保存 6 条与 18 条 MP4，并全部通过当时评分。伙伴对比核查发现，前五场景的实际动作/物体/时间轨迹一致，主要差异出现在 leave_and_return。',
         limit='Genesis 场景真实运行和渲染，不等于真实接触抓取。前五场景对三伙伴缺少行为区分力；这些运行没有机器人失败，不能证明失败恢复。',
         dirs=['genesis_v9','genesis_paired_v9','genesis_v10','genesis_paired_v10','dynamic_genesis_v2','task_catalog_genesis_v1'], code=['src/hrc_pilot/continuous_genesis.py','src/hrc_pilot/backend.py','src/hrc_pilot/continuous_report.py']),
    dict(id='e05', title='最初的历史反事实：从静态匹配走向行为解释', kind='参考后端 + 早期 Genesis',
         purpose='比较“直接执行”与“先求助”产生的不同协作过程，并尝试找出当前几何相同时的历史效应。',
         setup='在参考后端运行历史反事实，随后迁入 Genesis。记录匹配几何的步骤、伙伴反应和状态变化。',
         result='参考后端各版本保存两条对照。早期 history_counterfactual_genesis_v1 也保存两条视频，但后来发现 Genesis 没有兑现强制失败预算，需要修复后复核。',
         limit='此时只对齐部分几何，消息、占用等输入未完全匹配。旧 Genesis v1 不能当作已触发预定失败的证据。',
         dirs=['history_counterfactual_v1','history_counterfactual_v2','history_counterfactual_v3','history_counterfactual_verify','history_counterfactual_genesis_v1'], code=['src/hrc_pilot/continuous.py','src/hrc_pilot/backend.py']),
    dict(id='e06', title='失败预算修复与多 seed 恢复：同时保留负例', kind='Genesis / 合成失败',
         purpose='让声明的失败在 Genesis 中确实发生，区分“失败后恢复”“持续失败”和“从未失败”。',
         setup='补齐 robot_failure_budget。三个 seed 各运行 failure_handoff、failure_no_handoff、no_failure；另三个 seed 运行 persistent_failure。机器人失败由预算/概率注入，不是抓取接触失败。',
         result='Genesis 九条中：接管 3/3 完成，机器人自己重试 3/3 完成，无失败基线 3/3 完成。持续失败负例 0/3 完成，各发生 30 次失败。共 12 条视频。参考后端对应九条为 6/9，不能用 Genesis 结果替代。',
         limit='failure_no_handoff 能靠重试成功，不能当“没有接管就必然失败”的负例。no_failure 的恢复指标应为空，而不是恢复成功。活动成功也不等于机器人角色成功：接管时机器人原角色可能失败。',
         dirs=['recovery_reference_v1','recovery_genesis_v1','recovery_negative_genesis_v1'], code=['scripts/run_genesis_recovery.py','src/hrc_pilot/backend.py','src/hrc_pilot/dataset.py']),
    dict(id='e07', title='修复后的历史反事实：策略改变过程，但历史尚未隔离', kind='Genesis / 3 seed × 2 策略',
         purpose='在失败确实生效后复核，直接行动与先求助是否改变失败、接管和过程。',
         setup='seed 0、1、2，各运行 greedy_public 和 request_help 两个手写策略，共六条真实视频。',
         result='seed 0 的直接执行出现一次失败后由人接管；先求助条件没有启动会失败的搬运动作，因此没有失败。几何匹配分别覆盖 6 和 2 步。',
         limit='策略同时改变当前消息与占用，不能仅据这些差异归因于持久历史。因此后来增加严格匹配探针，而不是把此结果当作最终历史结论。',
         dirs=['history_counterfactual_genesis_v2','history_counterfactual_genesis_seed1','history_counterfactual_genesis_seed2'], code=['src/hrc_pilot/continuous.py','scripts/run_continuous_benchmark.py']),
    dict(id='e08', title='严格匹配历史探针：机制验证与冻结消融', kind='参考后端 → Genesis',
         purpose='把当前输入匹配起来，再检查公开历史更新是否会改变规则伙伴对同一求助的回答。',
         setup='三个 seed，各包含可靠/失败两个前缀，以及两段历史 × adaptive/frozen 四个探针。从公开观察重放更新状态，只将 trust/reliability 带入重建的探针世界；frozen 保持两值 0.7。Genesis v2 增补五项匹配核查。',
         result='三个 seed 的首次模型输入、RGB、动作，以及回答前完整伙伴输入、RGB，五项全部一致。可靠历史 trust/reliability 为 .78/.82，adaptive 3/3 接受；失败历史 .34/.16，3/3 拒绝；冻结两组均 3/3 接受。v2 保存 18 条视频，其中 6 个前缀复用 v1，12 个探针重新运行。',
         limit='证明所写历史规则会产生预期因果差异，不证明真人心理规律。探针重建了世界/协议，只携带两个变量，不是自然无重置持续活动；也没有真实 VLA 参与这组协作。',
         dirs=['matched_history_reference_v1','matched_history_genesis_v1','matched_history_genesis_v2'], code=['src/hrc_pilot/history_probe.py','scripts/run_matched_history_probe.py']),
    dict(id='e09', title='原生关节与双相机校准：为真模型动作建立通路', kind='Genesis / 几何 IK 教师',
         purpose='验证机器人可以直接接收关节动作，并从外部相机、腕部相机获得真实 RGB；检查夹爪宽度与距离关联的抓放记录。',
         setup='joint_calibration v1/v2 各一条。公开几何 IK 教师输出 18 个 joint_position 动作，1.2 秒；关节实际执行。',
         result='校准条目完成搬运，保存关节轨迹、双视角图像和视频，事件链为 attach → release → transfer。',
         limit='教师用几何求解，不是训练好的模型。靠近物体且夹爪关闭后仍是运动学绑定，打开在当前位置解除；没有以摩擦/接触形成真实抓取。',
         dirs=['joint_calibration_genesis_v1','joint_calibration_genesis_v2'], code=['src/hrc_pilot/robot_control.py','scripts/run_joint_calibration.py','src/hrc_pilot/backend.py']),
    dict(id='e10', title='π0.5-DROID 真模型闭环：接入成功，搬运未成功', kind='Genesis / 真实 VLA',
         purpose='让实际训练好的模型读取模拟相机和机器人状态并输出动作，区分“外部接口存在”与“模型确实运行”。',
         setup='官方 OpenPI π0.5-DROID 权重；只输入 exterior RGB、wrist RGB、7 关节状态、夹爪状态和任务文本。输出动作块，取前 8 步转换为关节目标，15Hz 执行。两条运行分别 6 秒、30 秒，人的动作都是 observe。',
         result='v1：12 次模型调用、90 个原生关节动作；v2：57 次调用、450 个动作。两条均 task_success=false，没有完成物品搬运。核查真实像素输入、关节目标重建与视频完整解码。动作块记录为 15×8。',
         limit='这证明真模型与 Genesis 的动作/观察闭环通了，尚未证明操作可用，更没有验证模型 HRC。相机、动作标定与训练分布未充分对齐；两条失败不能归因为“模型不会协作”。推理期间模拟暂停，尚未评测推理延迟对人的影响；v2 沿用服务随机流，不是严格时限对照。',
         dirs=['pi05_droid_genesis_v1','pi05_droid_genesis_v2','pi05_droid_dynamic_genesis_v2'], code=['src/hrc_pilot/openpi_adapter.py','scripts/run_openpi_benchmark.py','scripts/serve_openpi_droid.py','scripts/verify_openpi_run.py']),
    dict(id='e11', title='活动契约评分收紧：合法贡献、交接与前置关系', kind='Genesis / 评分回归',
         purpose='防止只要物体到了目标就判成功，重新核查是谁完成了什么、交接是否合法、前置任务是否满足。',
         setup='seed 0 复核四条件：接管、独自重试、无失败、持续失败；统一记录机器人角色成功、活动成功、交接与恢复状态。',
         result='四条为 3 成功、1 失败；成功条目的蓝杯合法贡献发生在红杯前置贡献之后。保存四条视频与视频/浏览器核查记录。',
         limit='这是手写基线和评分器回归，不是新模型效果提升。旧目录保留当时评分，不能直接合并成一张统一性能排名。',
         dirs=['recovery_contract_genesis_v2'], code=['src/hrc_pilot/continuous.py','scripts/run_genesis_recovery.py']),
    dict(id='e12', title='动态伙伴 + π0.5-DROID：首次联合纵切片', kind='Genesis / 真实 VLA + 动态伙伴',
         purpose='把真实训练模型、动态伙伴、公开反馈和真实 Sim 视频放到同一条连续运行中，检查联合接口是否真正闭环。',
         setup='固定 seed 0、15 Hz、约 30 秒；动态伙伴处理红杯，π0.5-DROID 只接收外部/腕部 RGB、7 个关节、夹爪和公开语言，负责蓝杯。伙伴的 profile、意图和记忆留在评测端，不输入模型；模型动作块直接转换为关节目标。',
         result='完成 57 次模型推理和 450 个关节控制步，记录 4 次伙伴意图切换、2 次公开记忆写入、96 次检索和 4 次反思。真实 Sim 视频 480 帧、15 FPS，所有输入、动作、事件和时间轴通过独立核查。红杯由人完成，蓝杯未完成，整体任务失败。',
         limit='这是联合链路和失败边界的纵切片，不是协作能力排行榜。模型尚未完成蓝杯，Genesis 抓放仍是运动学绑定，伙伴是程序化规则 profile，且只有一个 seed；不能据此断言模型没有 HRC 能力。',
         dirs=['pi05_droid_dynamic_genesis_v2'], code=['scripts/run_openpi_benchmark.py','src/hrc_pilot/continuous.py','src/hrc_pilot/continuous_report.py']),
]


def inventory():
    rows = []
    bases = [(ROOT / 'results/pilot_v1', True), (ROOT / 'results/continuous_v2', False)]
    for base, pilot in bases:
        directories = [base / 'formal'] if pilot else sorted(base.iterdir())
        for d in directories:
            if not d.is_dir():
                continue
            f = next((d / n for n in SUMMARY_FILES if (d / n).exists()), None)
            if f is None:
                continue
            data = load(f)
            episodes = data.get('episodes', [])
            provenance = load(d / 'provenance.json') if (d / 'provenance.json').exists() else data.get('provenance', {})
            for verification in sorted(d.glob('*verification.json')):
                load(verification)
            native = d.name.startswith('pi05_')
            backend = provenance.get('backend') or next((e.get('backend') for e in episodes if e.get('backend')), '未记录')
            category = 'vla' if native else ('genesis' if pilot or 'Genesis' in str(backend) else 'reference')
            rows.append(dict(name=d.name, path=str(d.relative_to(ROOT)), summary=str(f.relative_to(ROOT)),
                             report=str((d / 'index.html').relative_to(ROOT)) if (d / 'index.html').exists() else None,
                             backend=backend, category=category, count=len(episodes),
                             successes=sum(e.get('task_success') is True for e in episodes),
                             seeds=sorted({e.get('seed') for e in episodes if e.get('seed') is not None}),
                             scenes=sorted({e.get('scenario', '') for e in episodes}),
                             videos=[str(v.relative_to(ROOT)) for v in sorted(d.rglob('demo.mp4'))],
                             episode_files=[str(x.relative_to(ROOT)) for x in sorted(d.rglob('*'))
                                            if x.is_file() and x.name in {'events.jsonl','policy_io.jsonl',
                                                'public_observations.jsonl','trajectory.npz','history_probe.json',
                                                'partner_inputs.jsonl','metrics.json','preview.png'}],
                             files=[str(x.relative_to(ROOT)) for x in sorted(d.iterdir()) if x.is_file() and x.suffix == '.json']))
    return rows


def render():
    rows = inventory()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    timestamp = datetime.now().astimezone().isoformat(timespec='seconds')
    cards = []
    for i, stage in enumerate(STAGES, 1):
        text = ''.join(f'<div><h3>{label}</h3><p>{html.escape(stage[key])}</p></div>' for key, label in
                       [('purpose','要解决什么'),('setup','实际怎么做'),('result','观察到什么'),('limit','证据到哪里为止')])
        sources = ' · '.join(link(p, Path(p).name) for p in stage['code'])
        cards.append(f'<article id="{stage["id"]}" class="experiment"><div class="eyebrow">实验 {i:02d} · {stage["kind"]}</div><h2>{stage["title"]}</h2>{text}<h3>报告与原始结果</h3>{runs(stage["dirs"],stage.get("pilot",False))}<p class="source">实现文件：{sources}</p></article>')
    scenes = [
        ('relay / 顺序接力','先完成前置贡献，另一方再接续搬运；检查时序与交接。'),
        ('nested_support / 嵌套支持','在主要工作过程中加入支持子活动；检查支持与主任务依赖。'),
        ('concurrent_overlay / 并发叠加','多个工作项并行，支持/干预覆盖主活动；检查占用和贡献安排。'),
        ('history_reinterpretation / 历史重解释','依据此前公开过程调整当前解释与行动；早期场景对伙伴区分力弱，后来另做严格匹配。'),
        ('robot_induced_rebalance / 机器人诱发再分工','机器人延迟、失败或求助触发伙伴承担/重分配工作。'),
        ('leave_and_return / 暂离与返回','伙伴可用性变化时维持任务，返回后重新安排贡献。'),
    ]
    scene_html = ''.join(f'<tr><th scope="row">{a}</th><td>{b}</td></tr>' for a,b in scenes)
    table_rows = []
    for i,r in enumerate(rows,1):
        resources = (link(r['report'],'报告') + ' · ' if r['report'] else '') + link(r['summary'],'汇总 JSON')
        extras = ''.join('<li>' + link(p, Path(p).name) + '</li>' for p in r['files'] if p != r['summary'])
        videos = ''.join('<li>' + link(p, str(Path(p).relative_to(Path(r['path'])))) + '</li>' for p in r['videos'])
        episode_files = ''.join('<li>' + link(p, str(Path(p).relative_to(Path(r['path'])))) + '</li>' for p in r['episode_files'])
        category_name = {'vla':'真实 VLA','genesis':'Genesis 手写实验','reference':'参考后端 / 旧记录'}[r['category']]
        details = f'<details><summary>文件与视频 ({len(r["videos"])} 个 MP4)</summary><ul class="files">{extras}{videos}</ul></details>'
        details += f'<details><summary>逐条轨迹、事件、观察和动作</summary><ul class="files">{episode_files}</ul></details>'
        search = html.escape(' '.join([r['name'], *r['scenes'], category_name]), quote=True)
        table_rows.append(f'<tr data-kind="{r["category"]}" data-search="{search}"><td>{i:02d}</td><th scope="row"><code>{r["name"]}</code><div class="muted">{category_name}<br>{html.escape(str(Path(r["path"]).parent))}</div></th><td>{r["successes"]}/{r["count"]}<div class="muted">seed {", ".join(map(str,r["seeds"])) or "未记录"}</div></td><td>{resources}{details}<details><summary>场景</summary><p>{html.escape(", ".join(r["scenes"]))}</p></details></td></tr>')
    featured = [
        ('可靠历史 → 接受求助','matched_history_genesis_v2/seed_000/probe/reliable_adaptive/matched_history_probe/demo.mp4','E08：与失败历史匹配当前输入，仅携带历史状态。'),
        ('失败历史 → 拒绝求助','matched_history_genesis_v2/seed_000/probe/failures_adaptive/matched_history_probe/demo.mp4','E08：这是规则伙伴的状态效应，不是真人行为。'),
        ('失败后的人类接管','recovery_contract_genesis_v2/seed_000/failure_handoff/demo.mp4','E11：合成失败引发重分工，物品仍为吸附模型。'),
        ('π0.5-DROID：30 秒真实模型运行','pi05_droid_genesis_v2/pi05_droid_native/demo.mp4','E10：机器人真模型动作，人只观察，搬运未完成。'),
        ('π0.5-DROID + 动态伙伴联合运行','pi05_droid_dynamic_genesis_v2/pi05_droid_native/demo.mp4','E12：真实模型与动态伙伴同一时间轴运行，蓝杯未完成。'),
    ]
    video_html = []
    for title,relative,note in featured:
        path = 'results/continuous_v2/' + relative
        if not (ROOT/path).exists():
            raise FileNotFoundError(path)
        video_html.append(f'<figure><figcaption><strong>{title}</strong><p>{note}</p></figcaption><video controls preload="none" aria-label="{title}" src="../../{quote(path)}"></video><p>{link(path,"直接打开 MP4")}</p></figure>')
    capabilities = [
        ('场景与任务定义','声明式活动契约、前置依赖、交互结构、场景生成与导入。','src/hrc_pilot/continuous.py'),
        ('Dataset 与评测入口','按 episode 保存情境、公开观察、动作、事件、评分；支持批量生成/评测。未完成经验证的正式训练数据集与训练实验。','src/hrc_pilot/dataset.py'),
        ('模型观察/动作边界','通用外部策略接口与私有 evaluator 隔离；真 VLA 有 RGB/关节闭环。','src/hrc_pilot/benchmark.py'),
        ('视频与可追溯报告','Genesis RGB、MP4、轨迹、事件同步、独立 HTML。','src/hrc_pilot/continuous_report.py'),
        ('WLA 与其他先进模型','接口基础存在；本次目录没有已完成的 WLA 联合协作评测。','experiments/continuous_v2/benchmark_schema.md'),
    ]
    cap_html = ''.join(f'<tr><th scope="row">{a}</th><td>{b}<br>{link(c,Path(c).name)}</td></tr>' for a,b,c in capabilities)
    nav = ''.join(f'<a href="#{s["id"]}">{i:02d} {s["title"].split("：")[0]}</a>' for i,s in enumerate(STAGES,1))
    document = TEMPLATE.replace('@@TIME@@',timestamp).replace('@@REV@@',revision[:12]).replace('@@NAV@@',nav).replace('@@CARDS@@',''.join(cards)).replace('@@SCENES@@',scene_html).replace('@@ROWS@@',''.join(table_rows)).replace('@@VIDEOS@@',''.join(video_html)).replace('@@CAPS@@',cap_html).replace('@@COUNT@@',str(len(rows)))
    document = document.replace('@@DOCS@@',' · '.join(link(p,label) for p,label in [
        ('.codex/mds/idea.md','原始 idea'),('.codex/mds/idea-conversation.md','说明性对话'),
        ('experiments/continuous_v2/design.md','连续实验设计'),('experiments/continuous_v2/genesis_validation.md','Genesis 复核记录'),
        ('experiments/continuous_v2/benchmark_schema.md','模型/数据接口'),
        ('.codex/codex-gen-content/mds/continuous_v2/native-vla-validation-20261005.md','真模型与匹配历史复核')]))
    (HERE / 'index.html').write_text(document,encoding='utf-8')
    snapshot = dict(generated_at=timestamp,source_git_revision=revision,scope='existing_results_only_no_new_experiments',
                    ordering='research_progression_not_exact_wall_clock_order',runs=rows,source_sha256=SOURCES)
    (HERE / 'evidence.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'已生成 {HERE / "index.html"}；{len(rows)} 个已有结果目录。')


TEMPLATE = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HRC-Bench · Goal 实验进展总报告</title>
<style>
:root{--ink:#182b38;--muted:#4c6271;--accent:#125d72;--line:#d6e1e7;--paper:#fff;--bg:#f3f6f7;--warm:#fff3df}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:20px}body{margin:0;color:var(--ink);background:var(--bg);font:16px/1.8 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,video:focus-visible{outline:3px solid #c16c12;outline-offset:4px}h1,h2,h3{line-height:1.35;letter-spacing:-.02em}h1{font-size:clamp(28px,4vw,44px);margin:12px 0 22px}h2{font-size:25px;margin:10px 0 24px}h3{font-size:17px;margin:22px 0 8px}p{margin:8px 0 16px}code{font:14px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}header{background:#e6eff2;border-bottom:1px solid var(--line)}.wrap{max-width:1260px;margin:auto;padding:44px 28px}.eyebrow{color:var(--accent);font-size:14px;font-weight:700;letter-spacing:.04em}.lead{max-width:900px;font-size:19px}.meta,.muted,.source{font-size:14px;color:var(--muted)}.layout{display:grid;grid-template-columns:245px minmax(0,1fr);gap:32px;max-width:1260px;margin:28px auto;padding:0 28px}aside{position:sticky;top:18px;align-self:start;max-height:calc(100vh - 36px);overflow:auto;padding:16px 0}nav a{display:block;padding:7px 8px;font-size:14px;border-left:2px solid transparent;text-decoration:none}nav a:hover{background:#e6eff2;border-left-color:var(--accent)}main{min-width:0}.panel,.experiment{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:30px;margin-bottom:24px}.experiment{border-top:4px solid #6a9aa8}.notice{background:var(--warm);border-left:4px solid #ba751c;padding:18px 22px;margin:22px 0}.notice p:last-child{margin-bottom:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.summary-card{background:#f2f7f8;padding:20px;border-radius:8px}.summary-card strong{display:block;font-size:19px;margin-bottom:8px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:14px 12px}thead{background:#edf3f5}th{font-weight:650}tbody th{min-width:190px}.files{padding-left:20px;font-size:14px}.files li{margin:8px 0;overflow-wrap:anywhere}.source{border-top:1px solid var(--line);padding-top:16px;overflow-wrap:anywhere}figure{margin:0;padding:20px;background:#f2f7f8;border-radius:10px;min-width:0}figcaption p{font-size:14px;color:var(--muted)}video{display:block;width:100%;aspect-ratio:4/3;background:#152733;border-radius:6px}figure>p{font-size:14px;margin-bottom:0}.filters{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0}.filters label{flex:1;min-width:180px;font-size:14px;font-weight:650}input,select{display:block;font:inherit;background:white;color:var(--ink);border:1px solid #809aa8;border-radius:6px;width:100%;padding:10px;margin-top:6px}summary{cursor:pointer;color:var(--accent);padding:6px 0}details p{font-size:14px;overflow-wrap:anywhere}.jump{display:inline-block;margin-right:18px}.skip{position:absolute;left:15px;top:-60px;background:white;padding:8px;z-index:10}.skip:focus{top:12px}footer{padding:20px 0 44px;font-size:14px;color:var(--muted)}[hidden]{display:none!important}@media(max-width:900px){.layout{grid-template-columns:1fr;gap:8px}aside{position:static;max-height:none;padding:0}nav{display:flex;gap:6px;overflow:auto;padding-bottom:12px}nav a{white-space:nowrap;border-left:0;border-bottom:2px solid var(--line)}.grid{grid-template-columns:1fr}.wrap{padding:30px 20px}.layout{padding:0 16px}.panel,.experiment{padding:22px 18px}h2{font-size:22px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:white}.layout{display:block;padding:0}.wrap{padding:0}aside,.filters,.skip{display:none}.panel,.experiment{border:0;padding:14px 0;break-inside:avoid}.grid{display:block}figure{break-inside:avoid;margin-bottom:20px}video{display:none}header{background:white}.table-wrap{overflow:visible}a{color:#182b38}}
</style></head><body><a class="skip" href="#main">跳到报告正文</a>
<header><div class="wrap"><div class="eyebrow">HRC-BENCH / 已有证据总览</div><h1>围绕持续共同活动 Goal，<br>目前做了什么？</h1><p class="lead">已建立连续协作运行与数据记录底座，完成规则伙伴、手写机器人基线的机制实验，并接通 π0.5-DROID 真模型动作。现在已有一条真实模型 + 动态伙伴的联合纵切片，但<strong>“真具身模型与自适应人类伙伴持续协调”的能力验证仍未完成。</strong></p><p class="meta">快照：@@TIME@@ · 来源代码提交 @@REV@@ · 顺序按研究推进组织，不代表所有运行的精确日历顺序。</p><a class="jump" href="#videos">直接看真实 Sim 视频</a><a class="jump" href="#e01">按顺序阅读实验</a><a class="jump" href="#archive">找全部结果文件</a></div></header>
<div class="layout"><aside><nav aria-label="报告目录"><a href="#status">目前完成程度</a><a href="#mechanism">人和机器人怎样行动</a><a href="#scenes">六个连续场景</a>@@NAV@@<a href="#videos">重点视频</a><a href="#platform">平台与 Dataset</a><a href="#archive">全部结果文件</a><a href="#remaining">Goal 尚未完成部分</a></nav></aside><main id="main">
<section id="status" class="panel"><div class="eyebrow">先读这一页</div><h2>两条通路已分别验证，还没有合成目标中的实验</h2><div class="grid"><div class="summary-card"><strong>协作机制通路</strong>公开事件 → 规则伙伴状态更新 → 求助/接管/分工改变。大部分机器人策略也是手写的。</div><div class="summary-card"><strong>真实模型通路</strong>双相机 RGB + 关节状态 + 文本 → π0.5-DROID → 关节动作。两条搬运都未完成，人仅观察。</div></div><div class="notice"><p><strong>当前结果支持“机制可执行”和“模型链路已接通”，不能据此宣称持续 HRC benchmark 已经验证有效。</strong>没有 WLA 完成评测，没有真人研究，没有真实接触抓取，也没有真模型在历史、组合结构与再分工中的成功对照。</p></div><p>Goal 要评测的是：同一持续活动中，双方根据对方实际行为组织贡献，指导、共同执行、干预等结构能组合并演化，而不只是各自把物品送到目标。</p><p class="source">@@DOCS@@</p></section>
<section id="mechanism" class="panel"><h2>你问的人类、机器人和吸附，实际是什么？</h2><div class="table-wrap"><table><thead><tr><th>部分</th><th>当前实现</th><th>应怎样理解</th></tr></thead><tbody><tr><th scope="row">模拟人类</th><td>公开事件触发手写数值更新，再以效用打分、阈值与依赖规则选行为；Avatar 执行动作。</td><td>确实还是规则/打分算法。trust 等是可更改状态，不是经真人数据学习或校准的人类模型。</td></tr><tr><th scope="row">大部分实验的机器人</th><td>GreedyPublicPolicy 等手写公共策略；底层动作按阶段执行轨迹/IK。</td><td>可以在线重规划，但仍是人设计的规则和阶段控制，不是训练好的具身决策模型。</td></tr><tr><th scope="row">E10 的机器人</th><td>π0.5-DROID 输出动作块，转换为关节目标；机械臂与夹爪真实执行。</td><td>这两条确实由真 VLA 驱动，但还未完成搬运与协作。</td></tr><tr><th scope="row">物品拿放</th><td>语义搬运阶段吸附/自动放置；原生关节按距离/夹爪宽度绑定，打开后在当前位置解除。</td><td>仍是运动学近似。视频不能作为摩擦、碰撞、接触稳定性或真实抓取能力证据。</td></tr><tr><th scope="row">memory</th><td>公开历史/事件日志 + 可更新伙伴状态；机器人基线可读取公开历史。</td><td>比只保存当前位置多了历史，但如何归纳和更新仍由人写规则，不是学到的长期协作记忆。</td></tr></tbody></table></div><p class="meta">名称提醒：pilot 的 memory/static/reactive 是机器人策略；continuous 的 fixed_replay/reactive/adaptive 是伙伴算法。不要把它们当作同一套模型能力分级。</p></section>
<section id="scenes" class="panel"><h2>六个连续场景在测什么</h2><p>这是协作结构的简化可执行原型，主要以物品搬运作为基础操作，并非六套已成熟的真实接触任务。</p><div class="table-wrap"><table><thead><tr><th>场景</th><th>安排与检查点</th></tr></thead><tbody>@@SCENES@@</tbody></table></div></section>
@@CARDS@@
<section id="videos" class="panel"><h2>重点真实 Sim 视频</h2><p>以下直接引用已保存的 Genesis MP4；不自动播放。它们展示实际场景、机器人、Avatar 与物品过程，物体机制仍是上文说明的运动学吸附。短片可重复播放，并结合原报告事件时间线看。</p><div class="grid">@@VIDEOS@@</div></section>
<section id="platform" class="panel"><h2>除了实验，还完成了哪些平台工作</h2><div class="table-wrap"><table><thead><tr><th>模块</th><th>已经具备 / 当前边界</th></tr></thead><tbody>@@CAPS@@</tbody></table></div><p>数据目录与文件配对采用稳定 episode 路径与文件命名。这里的 <a href="evidence.json">evidence.json</a> 仅是报告来源快照与哈希，不编码训练数据配对关系。</p><p>主线程复核记录记载 58 项正式测试通过，并做过视频解码和浏览器检查。本报告汇总这些已有证据；本侧会话没有重跑模型、仿真或主实验测试。</p></section>
<section id="archive" class="panel"><h2>全部已保存结果：@@COUNT@@ 个目录</h2><p>包括 pilot 正式目录及 continuous_v2 顶层含汇总文件的目录。旧版本、修订版、复用前缀均保留以便审计；<strong>这些条目不能作为独立样本相加，也不能跨版本汇总成一个成功率。</strong>“通过/总条数”是各目录当时 task_success 字段，参考后端条目没有真实 Sim 视频。</p><div class="filters"><label for="search">搜索目录或场景<input id="search" type="search" placeholder="例如 matched_history、relay、pi05"></label><label for="kind">运行类别<select id="kind"><option value="all">全部</option><option value="genesis">Genesis 手写实验</option><option value="reference">参考后端 / 旧记录</option><option value="vla">真实 VLA</option></select></label></div><p id="count" role="status" aria-live="polite">显示 @@COUNT@@ / @@COUNT@@ 个目录</p><div class="table-wrap"><table id="archive-table"><thead><tr><th>序号</th><th>结果目录</th><th>当时通过/条数</th><th>HTML、数据与视频</th></tr></thead><tbody>@@ROWS@@</tbody></table></div><p id="empty" hidden>没有匹配的目录。请更换关键词或类别。</p></section>
<section id="remaining" class="panel"><h2>离 Goal 完成还缺什么</h2><ol><li><strong>先让真模型稳定操作。</strong>两条 π0.5-DROID 都没有搬运成功，需完成相机/动作标定、任务与分布对齐，建立可靠操作基线。</li><li><strong>把真模型接入协作条件。</strong>目前真模型与规则协作分别验证，尚未跑成“模型行动改变伙伴 → 伙伴反馈再改变模型组织贡献”的联合比较。</li><li><strong>建立有区分力的持续任务。</strong>早期五个场景三伙伴轨迹一致；严格历史探针又重建了世界。还需要真正保持同一活动的历史、分工和进度，组合/结构留出条件也要对齐基础操作难度。</li><li><strong>验证伙伴与物理近似的适用性。</strong>目前的人是自定义规则，抓放是吸附；正式能力结论需要说明并验证这些近似，必要时升级接触与人类行为来源。</li><li><strong>完成正式数据集与模型比较。</strong>已有记录/生成/评测接口，不等于已获得经验证的训练集、WLA 结果或多个先进具身模型的持续协作成绩。</li></ol><p>这些是现有证据的缺口说明，不表示本报告已启动新的实验。本次新增的是统一的可阅读报告入口。</p></section>
<footer>静态中文报告，可直接在浏览器打开。视频和实验数据沿用项目软链接，请保留仓库与数据盘路径。<a href="evidence.json">来源快照</a> · <a href="build_report.py">报告生成脚本</a> · <a href="#main">回到正文</a></footer>
</main></div><script>
const search=document.getElementById('search'),kind=document.getElementById('kind'),rows=[...document.querySelectorAll('#archive-table tbody tr')];
function filter(){const query=search.value.trim().toLocaleLowerCase();let count=0;for(const row of rows){const visible=(kind.value==='all'||row.dataset.kind===kind.value)&&row.dataset.search.toLocaleLowerCase().includes(query);row.hidden=!visible;if(visible)count++;}document.getElementById('count').textContent=`显示 ${count} / ${rows.length} 个目录`;document.getElementById('empty').hidden=count>0;}
search.addEventListener('input',filter);kind.addEventListener('change',filter);
</script></body></html>'''


if __name__ == '__main__':
    render()
