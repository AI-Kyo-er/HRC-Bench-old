"""持续 benchmark 的独立、可审计 HTML 报告。"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .continuous import CONTINUOUS_SCENARIOS, ContinuousScenario


def write_continuous_report(output: Path, results: list[dict[str, Any]],
                            scenarios: list[ContinuousScenario] | None = None) -> Path:
    success_count = sum(bool(result["task_success"]) for result in results)
    total_steps = sum(int(result["steps"]) for result in results)
    rows = []
    for result in results:
        rows.append(
            "<tr>"
            f"<td>{html.escape(result['scenario'])}</td>"
            f"<td>{html.escape(result.get('condition', ''))}</td>"
            f"<td>{html.escape(result.get('structure_family', ''))}</td>"
            f"<td>{html.escape(result.get('partner_mode', ''))}</td>"
            f"<td>{'通过' if result['task_success'] else '未通过'}</td>"
            f"<td>{result['steps']}</td><td>{result['robot_actions']}</td>"
            f"<td>{result['preemptions']}</td><td>{result['proximity_warnings']}</td>"
            f"<td>{result.get('response_latency_steps') if result.get('response_latency_steps') is not None else '—'}</td>"
            f"<td>{result.get('coordination_cost', 0):.1f}</td>"
            f"<td>{html.escape(', '.join(result['completed_skills']))}</td>"
            "</tr>"
        )
    scenario_cards = []
    scenario_catalog = scenarios or list(CONTINUOUS_SCENARIOS.values())
    for scenario in scenario_catalog:
        scenario_cards.append(
            f"<article><h3>{html.escape(scenario.name)}</h3>"
            f"<p>{html.escape(scenario.description)}</p>"
            f"<p>物体数：{len(scenario.objects)}；人的初始贡献："
            f"{html.escape(json.dumps(scenario.human_targets, ensure_ascii=False))}；"
            f"机器人收到的公开分工：{html.escape(json.dumps(scenario.robot_targets, ensure_ascii=False))}</p>"
            f"<p>结构：<code>{html.escape(scenario.structure.family)}</code>；"
            f"片段：{html.escape(' → '.join(scenario.structure.segments))}；"
            f"划分：<code>{html.escape(scenario.structure.split)}</code>；"
            f"条件：<code>{html.escape(scenario.condition)}</code></p>"
            f"<p class='note'>伙伴可用性是隐藏条件（{scenario.human_availability:.2f}），"
            f"离返触发由公开完成进度和概率模型共同决定。</p></article>"
        )
    body = f"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><title>HRC-Continuous v2</title>
<style>
body {{ font-family: system-ui, 'Noto Sans CJK SC', sans-serif; max-width: 1180px; margin: 36px auto; padding: 0 24px; color: #172033; background: #f6f8fb; }}
header, article, section {{ background: white; border: 1px solid #dbe2ed; border-radius: 12px; padding: 20px; margin: 14px 0; }}
h1 {{ margin: 0 0 8px; color: #153b68; }} h2 {{ color: #1e527e; }} h3 {{ margin: 0 0 8px; color: #175c62; }}
table {{ border-collapse: collapse; width: 100%; background: white; }} th, td {{ border-bottom: 1px solid #e2e8f0; padding: 9px; text-align: left; font-size: 14px; }} th {{ background: #edf4fa; }}
code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }} .note {{ color: #56657a; }}
</style>
<header><h1>HRC-Continuous v2：持续共同活动参考运行时</h1>
<p>本页记录的是可复现的 benchmark 运行和场景实例，不把参考伙伴的结果外推为 VLA 能力结论。结构条件与伙伴条件是实验变量，不能用一个固定状态机替代。</p>
<p class="note">同一 episode 中人和机器人逐 tick 同时推进；模型只能看到公开观测、RGB（若后端提供）和公开消息，不能读取场景目标、伙伴信任或可用性。</p></header>
<section><h2>实验目的</h2>
<p>这个 benchmark 测试机器人能否在同一个持续共同活动中保留公开约定、观察伙伴行为、执行自己的动作，并在指导、共同执行、干预、暂离和重新分工交织时重新组织双方贡献。测试单位是双方共同推进的 episode，而不是孤立的“听懂一句话”或单个抓取技能。</p>
<p>参考后端的成功率只用于检查协议和评测器能否工作；真正的模型比较应把同一场景实例和同一公开观测接口交给不同 VLA/WLA，再比较任务进展、依赖保留、协调代价和安全结果。固定回放、反应式和适应式伙伴用于区分“只完成预录动作”“响应当前公开行为”和“根据历史可靠性重组分工”。</p></section>
<section><h2>运行闭环</h2>
<ol><li>场景实例提供物体、区域、初始公开分工和隐藏伙伴条件；隐藏条件不会进入 <code>Observation</code>。</li>
<li>每个 tick 先推进伙伴的当前意图，再把公开消息、几何状态、RGB（若后端提供）和机器人动作阶段交给策略。</li>
<li>策略输出一个可持续的动作块（语义搬运、关节目标、求助、确认、等待或结束）；新公开消息可以在动作完成前打断它。</li>
<li>后端同时推进人和机器人，并记录真实物体位置、动作阶段、消息、接近事件和完成事件。</li>
<li>独立评测器根据终态和全程事件计算结果，模型不能通过输出 <code>finish</code> 伪造任务完成。</li></ol></section>
<section><h2>这版具体改变了什么</h2>
<ul><li>这不是按“第 N 步发生事件”的固定状态机：任务实例只定义物体、区域、分工和伙伴条件，双方每个 tick 根据当前公开观测重新选择下一步。</li>
<li>动作是可持续的 action chunk，执行中可以因公开消息或伙伴靠近而重新决策。</li>
<li>伙伴使用冻结参数的连续效用模型，根据距离、负载、信任和机器人当前占用选择目标；它会并行移动、抓取、放置、暂离和返回。</li>
<li>场景由物体、区域、公开分工、交互结构和私有伙伴参数组合而成；<code>generate_scenarios</code> 与 <code>generate_benchmark_suite</code> 可以改变布局、分工、结构划分和离返条件，不依靠预写的“第 N 步触发事件”推进。</li>
<li>每个 tick 保存公开观测、双方动作、物体位置、动作打断、接近警告和技能完成事件，便于接入真实 VLA/WLA 后复算同一指标。</li></ul></section>
<section><h2>场景目录</h2>{''.join(scenario_cards)}</section>
<section><h2>本次运行</h2><p>完成 {success_count}/{len(results)} 个 episode，共记录 {total_steps} 个 benchmark tick。</p><table><thead><tr><th>场景</th><th>条件</th><th>结构</th><th>伙伴</th><th>任务</th><th>仿真步</th><th>机器人动作</th><th>打断</th><th>接近警告</th><th>响应步数</th><th>协调代价</th><th>完成技能</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<section><h2>可用于数据集的产物</h2><p>每个场景目录包含 <code>scenario.json</code>（实例、结构条件和评测目标）、<code>public_observations.jsonl</code>（模型可见输入）、<code>policy_io.jsonl</code>（策略输入输出）、<code>trace.jsonl</code>（逐 tick 几何轨迹）、<code>events.jsonl</code>（事件审计）和 <code>metrics.json</code>（独立评分）。训练或评测加载器应按 episode 目录和文件 stem 配对，不需要额外关系清单。<code>held_out</code> 结构只依据 <code>scenario.json</code> 的 split 进入测试集。</p></section>
<section><h2>模型接入边界</h2><p><code>ModelPolicy</code> 将 VLA 的 RGB 加结构化观测或 WLA 的文本/状态观测转换成同一个动作协议。模型可以返回 JSON 字符串、JSON 对象或 <code>Action</code>；运行时检查动作类型、目标字段、关节维度和持续步数，再交给后端执行。参考的 <code>GreedyPublicPolicy</code> 只是协议基线，不能代表先进具身模型。</p></section>
<section><h2>证据边界</h2><p>参考后端用于验证协议、动态伙伴和评测逻辑；真实模型通过公开观测到动作的适配器接入，Genesis 后端仍需在相同场景实例和记录格式下完成接触动力学验证。当前结果不能当作真实 VLA/WLA 排行榜。</p></section>
</html>"""
    output.mkdir(parents=True, exist_ok=True)
    path = output / "index.html"
    path.write_text(body, encoding="utf-8")
    return path
