"""Offline HTML review, with comparisons from executed episodes only."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .scenarios import SCENARIOS


def write_dashboard(output: Path, results: list[dict]):
    rows, cards = [], []
    for row in results:
        name, policy, seed = row["scenario"], row["policy"], row["seed"]
        path = f"{name}__{policy.replace(':', '_')}__seed{seed}"
        success = row["task_success"]
        badge = "通过" if success else "未通过"
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{html.escape(policy)}</td><td>{seed}</td>"
                    f"<td class={'ok' if success else 'bad'}>{badge}</td>"
                    f"<td>{row['forbidden_red_transfers']}</td><td>{row['failed_skills']}</td>"
                    f"<td><a href='{path}/metrics.json'>指标</a> · <a href='{path}/events.jsonl'>事件</a> · "
                    f"<a href='{path}/policy_io.jsonl'>策略输入输出</a></td></tr>")
        cards.append(f"<article data-scenario='{html.escape(name)}' data-policy='{html.escape(policy)}'>"
                     f"<div class='card-head'><strong>{html.escape(name)}</strong><span>{html.escape(policy)} / {badge}</span></div>"
                     f"<p>{SCENARIOS[name].description}</p>"
                     f"<video controls preload='none' poster='{path}/preview.png' src='{path}/demo.mp4'></video>"
                     f"<p><a href='{path}/trajectory.npz'>状态轨迹</a> · <a href='{path}/post_intervention_state.json'>干预后状态</a></p></article>")
    counts = {p: [sum(r["task_success"] for r in results if r["policy"] == p),
                  sum(r["policy"] == p for r in results)] for p in dict.fromkeys(r["policy"] for r in results)}
    score = " · ".join(f"{html.escape(p)}：{n}/{total}" for p, (n, total) in counts.items())
    document = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HRC 合作重平衡 · Pilot v1</title><style>
:root{color-scheme:dark}body{margin:0;background:#0e1522;color:#e2eaf7;font:16px/1.7 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:36px 24px}h1{font-size:30px;line-height:1.35;margin-bottom:12px}a{color:#89cbff}p{color:#b7c6dc}.tag{color:#8edbc1;letter-spacing:2px}.notice{border-left:3px solid #e5c077;padding:12px 20px;background:#182133}table{border-collapse:collapse;width:100%;font-size:14px;margin:24px 0}th,td{text-align:left;border-bottom:1px solid #304057;padding:10px}.ok{color:#88dfb4}.bad{color:#ffadab}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:22px}article{background:#182133;border:1px solid #304057;border-radius:12px;padding:18px}article p{font-size:14px}.card-head{display:flex;justify-content:space-between;gap:12px}.card-head span{color:#89cbff}video{width:100%;border-radius:6px}select{background:#182133;border:1px solid #49617f;color:white;padding:9px;margin:12px 12px 8px 0;border-radius:6px}.scroll{overflow:auto}@media(max-width:500px){main{padding:20px 12px}.grid{grid-template-columns:1fr}}
</style><main><div class="tag">VC + GENESIS / PILOT V1</div>
<h1>Human-robot Progressively Rebalanced<br>Collaboration Benchmark</h1>
<p>共同活动中的约定保留、理解更新与分工修复。当前场景相同，历史或可用贡献不同，后续行为应随有效约定调整。</p>
<div class="notice">这是具身执行与评测机制的基础 demo。使用手写策略、仿真语义观测和运动学抓取抽象；这些结果不代表 VLA/LLM 的能力，也不验证接触力、抓握或人体安全。</div>
<h2>实际运行结果</h2><p>SCORE</p><div class="scroll"><table><thead><tr><th>条件</th><th>策略</th><th>Seed</th><th>任务结果</th><th>违约红杯搬运</th><th>技能失败</th><th>证据</th></tr></thead><tbody>ROWS</tbody></table></div>
<h2>查看执行</h2><select id="scenario"><option value="all">全部条件</option>SCENARIO_OPTIONS</select><select id="policy"><option value="all">全部策略</option>POLICY_OPTIONS</select><div class="grid">CARDS</div>
<p>蓝色区域为收纳区，绿色区域为个人留用区。每段视频对应真实生成的状态轨迹与独立评测结果。<a href="summary.json">完整结果</a> · <a href="provenance.json">运行版本</a> · <a href="episodes.csv">CSV</a></p>
</main><script>function filter(){const s=document.querySelector('#scenario').value,p=document.querySelector('#policy').value;document.querySelectorAll('article').forEach(a=>a.hidden=(s!=='all'&&a.dataset.scenario!==s)||(p!=='all'&&a.dataset.policy!==p));}document.querySelectorAll('select').forEach(s=>s.onchange=filter);</script></html>"""
    scenario_options = "".join(f"<option>{html.escape(n)}</option>" for n in dict.fromkeys(r["scenario"] for r in results))
    policy_options = "".join(f"<option>{html.escape(n)}</option>" for n in counts)
    for marker, content in [("SCORE", score), ("ROWS", "".join(rows)), ("CARDS", "".join(cards)),
                            ("SCENARIO_OPTIONS", scenario_options), ("POLICY_OPTIONS", policy_options)]:
        document = document.replace(marker, content)
    (output / "index.html").write_text(document)
