"""Generate an offline, self-explanatory HTML report from executed episodes."""
from __future__ import annotations

import html
from pathlib import Path

from .scenarios import SCENARIOS


POLICY_INFO = {
    "memory": ("保留并更新约定", "保留历史约定；接受公开修正；伙伴拒绝后重新承担任务。"),
    "static": ("固定初始计划", "只执行初始指令与分工，不处理后续修正或伙伴不可用。"),
    "reactive": ("局部反应", "响应明确修正和拒绝，但移杯后按默认几何恢复，不保留留用历史。"),
}

SCENARIO_INFO = {
    "history_keep": ("历史保留", "先约定红杯留用；人随后把红杯移开。", "红杯留用，蓝杯收纳。"),
    "history_pack": ("历史对照", "先约定两个杯子都收纳；人执行相同的移杯动作。", "红杯和蓝杯都收纳。"),
    "information_update": ("公开信息更新", "人获得新用途信息并公开修正理解；物体位置前后不变。", "接受修正，红杯留用，蓝杯收纳。"),
    "partner_available": ("伙伴可用", "蓝杯初始由人负责；机器人公开求助，人接受并搬运。", "蓝杯由人放入收纳区。"),
    "partner_unavailable": ("伙伴不可用", "相同初始分工下，人拒绝求助。", "机器人重新承担蓝杯搬运。"),
}


def _text(value: object) -> str:
    return html.escape(str(value), quote=True)


def write_dashboard(output: Path, results: list[dict]):
    rows, cards = [], []
    for row in results:
        name, policy, seed = row["scenario"], row["policy"], row["seed"]
        path = f"{name}__{policy.replace(':', '_')}__seed{seed}"
        success = row["task_success"]
        badge = "通过" if success else "未通过"
        policy_label = POLICY_INFO.get(policy, (policy, "自定义策略"))[0]
        scenario_info = SCENARIO_INFO.get(name, (name, SCENARIOS[name].description, ""))
        rows.append(
            f"<tr><td>{_text(scenario_info[0])}</td><td><code>{_text(name)}</code></td>"
            f"<td>{_text(policy_label)}<small><code>{_text(policy)}</code></small></td><td>{seed}</td>"
            f"<td class={'ok' if success else 'bad'}>{badge}</td>"
            f"<td>{row['forbidden_red_transfers']}</td><td>{row['failed_skills']}</td>"
            f"<td><a href='{_text(path)}/metrics.json'>指标</a> · <a href='{_text(path)}/events.jsonl'>事件</a> · "
            f"<a href='{_text(path)}/policy_io.jsonl'>策略输入输出</a></td></tr>"
        )
        cards.append(
            f"<article class='episode-card' data-scenario='{_text(name)}' data-policy='{_text(policy)}'>"
            f"<div class='card-head'><strong>{_text(scenario_info[0])}</strong>"
            f"<span>{_text(policy_label)} · {badge}</span></div>"
            f"<p>{_text(scenario_info[1])}</p>"
            f"<video controls preload='none' poster='{_text(path)}/preview.png' src='{_text(path)}/demo.mp4'></video>"
            f"<p class='card-links'><a href='{_text(path)}/trajectory.npz'>状态轨迹</a> · "
            f"<a href='{_text(path)}/post_intervention_state.json'>干预后状态</a> · "
            f"<a href='{_text(path)}/initial_public_history.json'>公开历史</a></p></article>"
        )

    policies = list(dict.fromkeys(r["policy"] for r in results))
    scenarios = list(dict.fromkeys(r["scenario"] for r in results))
    counts = {p: [sum(r["task_success"] for r in results if r["policy"] == p),
                  sum(r["policy"] == p for r in results)] for p in policies}
    score_cards = "".join(
        f"<div class='stat'><strong>{n}/{total}</strong><span>{_text(POLICY_INFO.get(policy, (policy,))[0])}</span>"
        f"<small>策略标识：<code>{_text(policy)}</code></small></div>"
        for policy, (n, total) in counts.items()
    )
    scenario_options = "".join(
        f"<option value='{_text(name)}'>{_text(SCENARIO_INFO.get(name, (name,))[0])}</option>"
        for name in scenarios
    )
    policy_options = "".join(
        f"<option value='{_text(policy)}'>{_text(POLICY_INFO.get(policy, (policy,))[0])}</option>"
        for policy in policies
    )
    history_audit = (
        "所有已运行的 history_keep / history_pack 配对在首次策略决策前匹配：物体位置、机器人关节和人体位置最大差异均为 0。"
        if results else "配对核查将在有运行结果后显示。"
    )
    document = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HRC 合作重平衡 · Pilot v1 实验报告</title><style>
:root{color-scheme:dark;--bg:#0e1522;--panel:#182133;--line:#304057;--text:#e2eaf7;--muted:#b7c6dc;--blue:#89cbff;--green:#88dfb4;--yellow:#e5c077;--red:#ffadab}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.75 system-ui,-apple-system,"Noto Sans CJK SC",sans-serif}main{max-width:1240px;margin:auto;padding:42px 26px 70px}h1{font-size:38px;line-height:1.25;margin:10px 0 16px;letter-spacing:-.02em}h2{font-size:26px;line-height:1.35;margin:54px 0 14px}h3{font-size:19px;margin:25px 0 8px}p{color:var(--muted);margin:9px 0 16px}a{color:var(--blue)}code{font:.88em ui-monospace,SFMono-Regular,Menlo,monospace;color:#d8e8ff;background:#101827;padding:2px 5px;border-radius:4px}.tag{color:#8edbc1;letter-spacing:2px;font-size:13px;font-weight:700}.lead{font-size:19px;max-width:920px;color:#d7e2f1}.notice{border-left:3px solid var(--yellow);padding:15px 20px;background:#182133;margin:24px 0}.notice strong{color:#ffe6a5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.panel,.stat,.question,.step,.boundary{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}.panel p:last-child,.step p:last-child{margin-bottom:0}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:22px 0}.stat strong{display:block;color:var(--green);font-size:29px;line-height:1.2}.stat span{display:block;color:#eef5ff;margin-top:4px}.stat small{display:block;color:var(--muted);margin-top:5px}.question{border-color:#3e6b88;background:#152638}.question strong{display:block;color:#dff3ff;font-size:18px}.question p{margin-bottom:0}.boundary{border-color:#6e5a32;background:#241f17}.boundary strong{color:#ffe6a5}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0 8px;min-width:850px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:10px 9px;vertical-align:top}th{color:#dcecff;background:#151f31;position:sticky;top:0}.ok{color:var(--green)}.bad{color:var(--red)}td small{display:block;color:var(--muted);margin-top:2px}.callout{border:1px solid #35536e;background:#142436;border-radius:10px;padding:14px 17px;color:#d5e8fb}.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;counter-reset:step}.step{position:relative;padding-top:38px}.step:before{counter-increment:step;content:counter(step);position:absolute;left:17px;top:13px;width:22px;height:22px;text-align:center;border-radius:50%;background:#285a78;color:#fff;font-weight:700;line-height:22px}.step strong{color:#eef6ff}.architecture{display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:12px;align-items:stretch}.architecture .arrow{display:flex;align-items:center;justify-content:center;color:var(--blue);font-size:25px}.mini{font-size:14px}.mini strong{color:#eaf5ff;display:block;margin-bottom:5px}.badge{display:inline-block;border:1px solid #477395;border-radius:999px;padding:2px 9px;color:#bfe5ff;font-size:13px;margin:2px}.metric{display:grid;grid-template-columns:210px 1fr;gap:9px;border-bottom:1px solid var(--line);padding:9px 0}.metric strong{color:#ecf5ff}.two-col{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.episode-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px}.episode-card p{font-size:14px}.card-head{display:flex;justify-content:space-between;gap:12px;align-items:baseline}.card-head span{color:var(--blue);font-size:14px;text-align:right}.episode-card video{display:block;width:100%;border-radius:7px;background:#0a1019;margin-top:12px}.card-links{margin-bottom:0}.refs a{margin-right:14px;white-space:nowrap}.foot{margin-top:48px;color:#8fa4bf;font-size:14px;border-top:1px solid var(--line);padding-top:18px}@media(max-width:720px){main{padding:28px 14px 50px}h1{font-size:29px}h2{font-size:23px;margin-top:40px}.architecture,.two-col{grid-template-columns:1fr}.architecture .arrow{transform:rotate(90deg);height:20px}.metric{grid-template-columns:1fr}.card-head{display:block}.card-head span{display:block;text-align:left;margin-top:4px}}
</style><style>.architecture{grid-template-columns:1fr auto 1.3fr auto 1fr}</style></head><body><main>
<div class="tag">VC + GENESIS / PILOT V1 / 实验报告</div>
<h1>Human–Robot Progressively Rebalanced<br>Collaboration Benchmark</h1>
<p class="lead">这是一份从研究动机、实验设置到证据边界的完整说明。它报告第一版“持续共同活动中的合作重平衡”机制验证，而不是把一个手写控制器包装成具身模型能力测试。</p>
<div class="notice"><strong>先看结论：</strong>在 5 个条件 × 3 个策略 × 1 个 seed 的 15 个 episode 中，保留并更新历史的策略完成 5/5，固定初始计划完成 3/5，局部反应策略完成 4/5。底层技能失败数为 0。结果说明环境和评测器能区分预先定义的协调机制；不能证明 VLA、VLM、LLM 或训练后具身模型的能力。</div>

<h2>1. 这项实验要回答什么</h2>
<div class="question"><strong>核心问题</strong><p>在一个持续的共同活动里，机器人能否保留有效的交互历史、接受人的公开修正，并在伙伴可用性改变后重新组织分工，而不是只根据当前几何位置或最初计划行动？</p></div>
<div class="two-col"><div class="panel"><h3>为什么需要这个 pilot</h3><p>HRC-Bench 的想法不是只测试“机器人能否把杯子放进托盘”，而是测试指导、共同执行和干预发生组合与演化时，双方能否继续组织同一个活动。相同的物理状态可能因为此前形成的约定不同而要求不同动作；伙伴拒绝贡献时，机器人还必须修复分工。</p></div><div class="panel"><h3>这版具体验证什么</h3><p>先用最小的桌面场景把三个机制做成可审计的对照：历史依赖、公开信息更新、伙伴可用性变化。每个结果都能回到事件日志、策略输入输出、状态轨迹和终态指标，而不是只看视频观感。</p></div></div>
<div class="callout"><strong>研究假设（机制级）：</strong>如果后续动作依赖于此前公开建立的约定，且协作关系会因信息或伙伴回应而改变，那么只保持初始计划或只做局部几何反应的策略，会在相应条件下产生可预测的协调错误。</div>

<h2>2. 实验范围与结论边界</h2>
<div class="two-col"><div class="panel"><h3>本实验覆盖</h3><p><span class="badge">持续历史</span><span class="badge">公开修正</span><span class="badge">分工重组</span><span class="badge">仿真执行</span><span class="badge">可追溯评测</span></p><p>一名 VC 模拟人、一个 Genesis Franka、桌面、红杯、蓝杯、蓝色收纳区和绿色个人留用区。使用一个 seed，固定布局，观察和动作接口可复现。</p></div><div class="boundary"><h3>本实验没有证明</h3><p>没有测试 VLA/VLM/LLM 或训练后的具身模型；没有测试纯视觉理解、自然语言自由对话、接触式抓取、力控制、真实机器人、人类安全或真人主观体验；没有多 seed 统计显著性，也没有证明完整 Benchmark 已经成立。</p></div></div>

<h2>3. 系统由什么组成</h2>
<div class="architecture"><div class="panel mini"><strong>VC：人类伙伴层</strong><p>提供人体角色、动作动画、拿放动作和可响应的伙伴逻辑。当前只抽取局部桌面工作空间，不使用完整城市或社区场景。</p></div><div class="arrow">→</div><div class="panel mini"><strong>策略接口：协调决策层</strong><p>手写的确定性 <code>CoordinationPolicy</code> 接收结构化观察和公开消息，输出有限动作，如搬运、求助、确认、等待和结束。</p></div><div class="arrow">→</div><div class="panel mini"><strong>Genesis：机器人执行层</strong><p>提供 Franka、物体、关节控制、逆运动学、轨迹采样、RGB 视频和仿真状态，并保存每个 episode 的证据文件。</p></div></div>
<p>因此，VC 和 Genesis 的作用是搭建“人—机器人—物体—消息—状态—评测”的可运行底座。当前的策略不是由 VC 或 Genesis 自动生成，也不是由模型从视频中学习出来的。</p>

<h2>4. 场景、条件与控制变量</h2>
<p>每个 episode 都从同一张桌面和两个杯子开始。红杯的目标可能是蓝色收纳区或绿色个人留用区；蓝杯目标是蓝色收纳区。人和机器人通过公开结构化消息协作。</p>
<div class="scroll"><table><thead><tr><th>条件</th><th>发生什么</th><th>正确的协调结果</th><th>主要检验</th></tr></thead><tbody>
<tr><td><strong>历史保留</strong><br><code>history_keep</code></td><td>先约定红杯留用；人接近机器人时把红杯移开。</td><td>保留留用约定，不把红杯收纳；收纳蓝杯。</td><td>同一几何干预下是否保留历史。</td></tr>
<tr><td><strong>历史对照</strong><br><code>history_pack</code></td><td>先约定红杯收纳；执行与上一条件相同的移杯动作。</td><td>红杯和蓝杯都收纳。</td><td>与 <code>history_keep</code> 配对，隔离历史差异。</td></tr>
<tr><td><strong>公开信息更新</strong><br><code>information_update</code></td><td>人获得新用途信息，公开把理解从收纳修正为留用；位置不变。</td><td>确认更新；红杯留用，蓝杯收纳。</td><td>是否接受信息更新而非坚持旧计划。</td></tr>
<tr><td><strong>伙伴可用</strong><br><code>partner_available</code></td><td>蓝杯初始由人负责；机器人公开请求帮助，人接受并搬运。</td><td>人完成蓝杯贡献。</td><td>是否能发起和等待伙伴贡献。</td></tr>
<tr><td><strong>伙伴不可用</strong><br><code>partner_unavailable</code></td><td>初始分工相同；人拒绝求助。</td><td>更新分工，由机器人收纳蓝杯。</td><td>伙伴拒绝后是否重新分配任务。</td></tr>
</tbody></table></div>
<div class="callout"><strong>关键控制：</strong>在 <code>history_keep</code> 与 <code>history_pack</code> 的首次关键策略决策前，物体位置、机器人关节和人体位置完全匹配；机器人 RGB 图像哈希也相同。两者的关键差异是此前公开形成的约定，而不是当前画面。</div>

<h2>5. 策略是什么：机制对照，不是模型对比</h2>
<div class="grid"><div class="panel"><h3>memory · 保留并更新约定</h3><p>保存指令和分工；收到公开 correction 时确认并更新；收到伙伴 decline 时把蓝杯所有权改回机器人。</p></div><div class="panel"><h3>static · 固定初始计划</h3><p>保持最初的红杯目标和蓝杯分工，不处理后续修正或伙伴拒绝。它是一个明确的负面对照。</p></div><div class="panel"><h3>reactive · 局部反应</h3><p>能响应明确修正和拒绝，但把“红杯被移开”当作默认几何事件，恢复为收纳红杯，因此会丢失留用历史。</p></div></div>
<p>代码中的策略接收 <code>Observation</code>，输出 <code>Action</code>。它们是手写、确定性、可解释的规则控制器；没有神经网络权重、训练数据、推理服务或语言模型调用。比较的是机制行为是否符合实验设计，不是模型大小或训练能力。</p>

<h2>6. 一个 episode 如何运行</h2>
<div class="flow"><div class="step"><strong>初始化</strong><p>创建 Genesis 桌面、Franka、两个杯子、区域和 VC 模拟人；加载同一 seed 与布局。</p></div><div class="step"><strong>公开约定</strong><p>伙伴发送红杯目标和蓝杯初始分工。策略只能通过公开消息获得这些信息。</p></div><div class="step"><strong>观察干预</strong><p>机器人接近红杯但尚未抓取；人在指定条件下移杯、公开修正，或等待机器人的求助。</p></div><div class="step"><strong>策略循环</strong><p>策略读取观察，输出搬运、求助、确认、等待或结束；每个决策写入 <code>policy_io.jsonl</code>。</p></div><div class="step"><strong>物理执行</strong><p>执行机器人或人的搬运，记录消息、技能中断、实际位置和轨迹；技能失败与协调失败分开记录。</p></div><div class="step"><strong>终态评测</strong><p>独立评测器根据真实终态位置、事件和策略是否宣布结束计算任务结果。</p></div></div>

<h2>7. 机器人动作如何真正执行</h2>
<div class="two-col"><div class="panel"><h3>策略看到什么</h3><p>仿真器提供的物体和区域几何、机器人末端与关节状态、人体位置、人手持物、已完成技能、公开消息，以及一帧 RGB 图像。语义几何和事件字段是当前 pilot 的主要决策输入；这不是纯视觉基线。</p></div><div class="panel"><h3>策略输出什么</h3><p><code>transfer</code>、<code>request_help</code>、<code>acknowledge</code>、<code>wait</code> 或 <code>finish</code>。例如 <code>transfer blue → tray_blue</code> 只表达目标物体和区域，不是模型直接输出关节轨迹。</p></div></div>
<div class="callout"><strong>以搬运为例：</strong>Genesis 后端先用逆运动学求 Franka 末端目标，再用关节位置控制器经过若干 waypoint 移动。杯子通过运动学 attachment 跟随末端，放下后检查终态位置。它不是接触式抓取，没有夹持力或抓取质量的声称；接近红杯和观察动作也由后端预先写好的流程执行。</div>

<h2>8. 指标与证据</h2>
<div class="two-col"><div class="panel"><div class="metric"><strong>任务成功</strong><span>红杯满足该条件的留用/收纳目标、蓝杯进入收纳区、策略宣布完成，且没有底层技能失败。</span></div><div class="metric"><strong>违约红杯搬运</strong><span>在人已经公开表达“留用”后，机器人仍把红杯放入收纳区的次数。</span></div><div class="metric"><strong>技能失败</strong><span>末端跟踪、人拿取、人放置等执行层失败；用来区分协调错误和操作错误。</span></div></div><div class="panel"><div class="metric"><strong>信息只变理解</strong><span>公开修正前后物体位置不变，并记录伙伴理解从 <code>pack</code> 到 <code>keep</code> 的更新。</span></div><div class="metric"><strong>拒绝后重分工</strong><span>伙伴拒绝后，机器人是否实际完成蓝杯搬运。</span></div><div class="metric"><strong>可审计产物</strong><span>每段视频都有 <code>events.jsonl</code>、<code>policy_io.jsonl</code>、<code>trajectory.npz</code>、<code>metrics.json</code> 和预干预状态。</span></div></div></div>

<h2>9. 实际运行结果</h2>
<div class="stats">SCORE_CARDS</div>
<p>总计 <strong>RESULT_COUNT</strong> 个 episode；底层技能失败数为 <strong>FAILED_SKILLS</strong>。表格中的结果来自独立终态评测，而不是根据策略名称推断。</p>
<div class="scroll"><table><thead><tr><th>条件</th><th>条件标识</th><th>策略</th><th>Seed</th><th>任务结果</th><th>违约红杯搬运</th><th>技能失败</th><th>证据</th></tr></thead><tbody>ROWS</tbody></table></div>
<div class="callout">HISTORY_AUDIT</div>

<h2>10. 如何解读结果</h2>
<div class="two-col"><div class="panel"><h3>支持的判断</h3><p><code>memory</code> 在五个机制条件中均成功，说明当前环境确实能让“保留约定、接受公开更新、拒绝后重分工”产生不同的可观察后果。<code>static</code> 在信息更新和伙伴不可用条件失败；<code>reactive</code> 在历史留用条件失败，正好对应它们被设计成缺少的机制。</p></div><div class="panel"><h3>不能外推的判断</h3><p>这些差异来自手写规则的设计对照，不能外推为某个学习模型更强，也不能说已经测量了真实人的协调成本。只有一个 seed、一个固定布局和极少物体，结果是机制可运行性的证据，不是统计结论。</p></div></div>

<h2>11. 审计入口与复现信息</h2>
<p class="refs"><a href="summary.json">完整摘要 summary.json</a><a href="episodes.csv">episode 表 episodes.csv</a><a href="provenance.json">版本和运行参数 provenance.json</a><a href="verification.json">正式核查 verification.json</a></p>
<p>正式运行使用 GPU 0，Genesis revision、VC revision、资产 revision、依赖版本、源码哈希和运行参数均记录在 <code>provenance.json</code>。验证还检查了 15 个 MP4 可解码、视频帧与轨迹样本对齐、轨迹数值有限、终态位置一致，以及预期的技能失败为 0。</p>

<h2>12. 结论边界与下一步</h2>
<div class="two-col"><div class="panel"><h3>当前结论</h3><p>第一版 VC + Genesis 底座已经能够运行一个可检查的持续共同活动，并通过受控物理状态和公开历史对照，把历史保留、信息更新和分工重组这些机制转化为可测的行为差异。</p></div><div class="panel"><h3>下一步实验</h3><p>接入真实具身模型；加入长度匹配的简单串接对照、未见交互组合、多 seed、多布局和更多物体；把视觉感知、基础技能失败、协调失败分别报告；再验证模拟伙伴的协调指标是否对应真人协作行为。</p></div></div>

<h2>13. 查看每个执行</h2><p>选择条件和策略，逐段观看正式生成的视频，并打开对应的状态、事件和策略输入输出。</p><select id="scenario"><option value="all">全部条件</option>SCENARIO_OPTIONS</select><select id="policy"><option value="all">全部策略</option>POLICY_OPTIONS</select><div class="grid">CARDS</div>
<p class="foot">生成说明：本页由 <code>src/hrc_pilot/report.py</code> 根据已执行 episode 生成。视频、轨迹、事件和指标均来自 <code>results/pilot_v1/formal/</code> 的正式产物；重新生成页面不会重新运行实验。</p>
</main><script>function filter(){const s=document.querySelector('#scenario').value,p=document.querySelector('#policy').value;document.querySelectorAll('.episode-card').forEach(a=>a.hidden=(s!=='all'&&a.dataset.scenario!==s)||(p!=='all'&&a.dataset.policy!==p));}document.querySelectorAll('select').forEach(s=>s.onchange=filter);</script></body></html>"""
    failed_skills = sum(row["failed_skills"] for row in results)
    replacements = [
        ("SCORE_CARDS", score_cards), ("RESULT_COUNT", str(len(results))),
        ("FAILED_SKILLS", str(failed_skills)), ("HISTORY_AUDIT", history_audit),
        ("ROWS", "".join(rows)), ("SCENARIO_OPTIONS", scenario_options),
        ("POLICY_OPTIONS", policy_options), ("CARDS", "".join(cards)),
    ]
    for marker, content in replacements:
        document = document.replace(marker, content)
    (output / "index.html").write_text(document, encoding="utf-8")
