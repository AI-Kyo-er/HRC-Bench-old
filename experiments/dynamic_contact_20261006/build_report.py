"""从真实产物重建本阶段研究报告，不运行模型或改写原始评分。"""
from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESULTS = ROOT / "results/continuous_v2"
NATIVE = RESULTS / "pi05_qwen_contact_benchmark"
CALIBRATION = RESULTS / "contact_calibration_formal"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def link(path, text):
    relative = "../../" + path.relative_to(ROOT).as_posix()
    return f'<a href="{escape(relative)}">{escape(text)}</a>'


def main():
    summary = read(NATIVE / "summary.json")
    provenance = read(NATIVE / "provenance.json")
    names = {"relay": "接力：人先完成前置贡献", "concurrent_overlay": "并行：双方各自操作",
             "robot_induced_rebalance": "重新协调：伙伴观察机器人进度"}
    tables, panels, evidence = [], [], []
    decisions = 0
    for metric in summary["episodes"]:
        directory = NATIVE / metric["scenario"]
        motion = read(directory / "motion_verification.json")
        physics = read(directory / "physics_contract.json")
        human_io = [json.loads(line) for line in (directory / "human_policy_io.jsonl").read_text().splitlines()]
        decisions += len(human_io)
        calls = next(row["model_calls"] for row in provenance["episode_model_calls"]
                     if row["scenario"] == metric["scenario"])
        robot = [value for value in metric["completed_skills"] if value.startswith("robot:")]
        human = [value for value in metric["completed_skills"] if value.startswith("human:")]
        tables.append(f'<tr><td>{names[metric["scenario"]]}</td><td>{"通过" if metric["task_success"] else "失败"}</td>'
                      f'<td>{len(robot)} / {len(human)}</td><td>{calls} / {len(human_io)}</td>'
                      f'<td>{metric["completion_time_s"]:.2f} 秒</td><td>未通过：{motion["violation_count"]} 次跳变</td></tr>')
        base = "../../" + directory.relative_to(ROOT).as_posix()
        panels.append(f'''<article><h3>{names[metric["scenario"]]}</h3>
<p>机器人合法贡献 {len(robot)} 项，人合法贡献 {len(human)} 项。原始活动评分：{"通过" if metric["task_success"] else "失败"}。
人体拿放最大单物理帧位移 {motion["maximum_human_object_displacement_per_physics_step_m"]:.3f} 米，不能纳入正式能力排名。</p>
<video controls preload="metadata" poster="{base}/preview.png" src="{base}/demo.mp4"></video>
<p>{link(NATIVE / 'index.html', '逐事件报告与双相机输入')} · {link(directory / 'motion_verification.json', '动作异常详情')}
 · {link(directory / 'human_policy_io.jsonl', '人类模型实际决策')} · {link(directory / 'policy_io.jsonl', '机器人实际动作块')}</p></article>''')
        evidence.append({"scenario": metric["scenario"], "robot_contributions": robot, "human_contributions": human,
                         "model_calls": calls, "human_decisions": len(human_io), "motion": motion,
                         "physics_grasp_objects": physics["contact_grasp_objects"]})
    calibration_episode = CALIBRATION / "joint_grasp_calibration"
    calibration_metric = read(calibration_episode / "metrics.json")
    calibration_video = "../../" + calibration_episode.relative_to(ROOT).as_posix()
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>动态人类与真实接触 HRC · 阶段报告</title>
<style>
:root{{color-scheme:light;--ink:#182c3d;--muted:#536578;--accent:#136c72}}
*{{box-sizing:border-box}}body{{margin:0;background:#f2f5f5;color:var(--ink);font-family:system-ui,"Noto Sans CJK SC",sans-serif;line-height:1.75}}
main{{max-width:1100px;margin:auto;padding:36px 24px 72px}}header{{padding:32px;border-radius:18px;background:#123440;color:white}}
h1{{font-size:clamp(25px,4vw,40px);line-height:1.35;margin:8px 0 20px}}h2{{margin:0 0 14px;font-size:24px}}h3{{font-size:20px}}
.eyebrow{{color:#ade1d2;font-size:14px;letter-spacing:1px}}section{{padding:28px;background:white;border-radius:16px;margin:24px 0}}
.warning{{border-left:5px solid #c17827;background:#fff5e8;padding:18px 22px;margin:20px 0}}a{{color:var(--accent);text-underline-offset:3px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}}.stat{{padding:18px;background:#e8f0ee;border-radius:12px}}
.stat strong{{display:block;font-size:28px}}.stat span{{color:var(--muted);font-size:14px}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:800px;font-size:14px}}
th,td{{text-align:left;border-bottom:1px solid #dce5e7;padding:13px 10px;vertical-align:top}}th{{background:#edf3f4}}
video{{width:100%;max-height:720px;background:#112234;border-radius:12px}}article{{margin:28px 0 38px;padding-top:12px;border-top:1px solid #dae3e6}}
.quiet{{color:var(--muted);font-size:14px}}code{{background:#edf1f2;padding:2px 5px;border-radius:4px}}@media(max-width:650px){{main{{padding:18px 12px 40px}}header,section{{padding:21px 17px}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><main><header><div class="eyebrow">HRC CONTINUOUS · 2026-10-06 · 目标仍在进行</div>
<h1>真实接触已经接通；联合运行暴露了人体拿放问题</h1>
<p>本阶段把真实 π0.5 机械臂、生成式 Qwen 人类伙伴与自由刚体场景放入同一条运行。
机器人不再通过吸附或目标坐标搬运物体；人的意图由语言模型生成。真实视频和动作记录同时暴露了当前系统仍不具备正式评测资格的原因。</p></header>
<div class="stats"><div class="stat"><strong>4 条</strong><span>新保存并核验的 Sim 视频</span></div>
<div class="stat"><strong>{provenance['model_calls']} 次</strong><span>真实 π0.5 模型推理</span></div>
<div class="stat"><strong>{decisions} 次</strong><span>Qwen 自主意图决策</span></div>
<div class="stat"><strong>0 / 3</strong><span>联合任务中的机器人合法贡献</span></div></div>
<section><h2>为什么做这组实验</h2>
<p>原来的规则伙伴与运动学吸附只能核查协议。这里要直接观察：训练好的具身模型负责操作时，生成式伙伴能否依据双方的公开进度改变自己的贡献，以及场景是否真的支持可信的动态 HRC 评测。</p>
<p>研究方向仍是动态人的政策与持续协调。模型是否“会合作”，必须在基本操作可用、动作时间合理、贡献归属可信的前提下判断。</p></section>
<section><h2>设置与可解释边界</h2>
<p>三类活动，均为 seed 0，最长 20 秒模拟时间。机器人使用官方 π0.5-DROID 权重，以 15 Hz 接收外部/腕部相机、本体状态和公开指令，实际输出关节动作。Qwen3-14B 使用 cooperative 人格，读取公开几何、公开消息和最近公开决定，生成接近、搬运、观察、让行、离返与公开表达；41 次输出没有 JSON 解析错误。</p>
<p>收纳块为 50×50×100 毫米、0.10 千克的自由刚体，受重力、碰撞和夹爪摩擦作用。
机器人目标速度有限制，保存请求值与实际施加值；提交机器人贡献需要双指受力接触、抬起、释放和至少 0.4 秒稳定支撑。没有用 IK 教师替模型执行。</p>
<div class="warning">人体仍使用 VC 的运动学拿放。动作核查发现单帧约 1 米的跳变，因此三条联合运行仅作诊断，不能纳入正式 Benchmark。
推理期间模拟时钟暂停，尚未测量模型延迟对正在活动的人产生的影响。伙伴记忆仍只有有限公开上下文，尚未实现 COOPERA 级别的长时段行为。</div></section>
<section><h2>机器人真实抓放：先核查场景是否可操作</h2>
<p>独立几何 IK 教师在 {calibration_metric['completion_time_s']:.2f} 秒内完成蓝块收纳。
实际双指摩擦夹持将物体抬高约 13 厘米，打开夹爪后物体回落到桌面并稳定。该校准通过动作连续性检查。
它证明这套物理场景可以完成抓放，不代表 π0.5 或 HRC 的成绩。</p>
<video controls preload="metadata" poster="{calibration_video}/preview.png" src="{calibration_video}/demo.mp4"></video>
<p>{link(CALIBRATION / 'index.html', '完整抓放校准报告')} · {link(calibration_episode / 'contacts.jsonl', '逐物理步接触记录')}
 · {link(calibration_episode / 'motion_verification.json', '动作核验')}</p></section>
<section><h2>联合运行结果：谁实际完成了工作</h2>
<div class="table-wrap"><table><thead><tr><th>活动</th><th>原始活动评分</th><th>机器人 / 人贡献项</th><th>π0.5 / Qwen 调用</th><th>模拟时长</th><th>动作资格</th></tr></thead>
<tbody>{''.join(tables)}</tbody></table></div>
<p>前两条由 Qwen 伙伴主动接管后完成，机器人在三条任务中均没有合法贡献，也未记录物理抓取成功。
这里的“活动通过”只说明评测器在当前执行抽象下检查到了终态，不能被读成机器人成功率。</p>
{''.join(panels)}</section>
<section><h2>这轮能支持什么结论</h2>
<p>已确认真实模型驱动关节、生成式伙伴选择意图、自由刚体接触与多活动契约可以共同运行。
已确认原有“任务成功”会掩盖机器人零贡献，人体执行器的瞬间拿放还会破坏真实时间与操作难度。</p>
<p>这轮无法回答先进具身算法是否具备持续 HRC 或 cobalance 能力：机器人基本操作尚未成功，人体动作又未通过连续性检查。
不使用手工加权总分掩盖这两个问题，也不把这些诊断样本计入成熟 Benchmark 的结果。</p>
<h3>继续推进的优先级</h3><ol><li>替换人体拿放执行器：连续接近、可见接触、物理持握与释放，取消坐标跳变，并把 Avatar 全身与实际物体动作对齐。</li>
<li>在合适的操作分布中建立真实模型的基础操作表现，再评测其对人类改变意图、接管、让行和重新分工的响应。</li>
<li>把真实操作扩展到现有九类活动契约、未见伙伴与任务组合；在同一世界内保留公开历史，再运行多模型、多 seed 的正式比较。</li></ol></section>
<section><h2>视频、复核与原始证据</h2><p>重要实验入口已强制在 HTML 生成前解码每条视频，并严格检查帧数、FPS 与事件时间轴。
另外复核的 7 组已有重要实验共 40 条视频均通过。轨迹用于审计，真实场景视频为主要视觉证据。</p>
<p>{link(NATIVE / 'video_verification.json', '联合运行视频核验')} · {link(CALIBRATION / 'video_verification.json', '抓放校准视频核验')}
 · {link(NATIVE / 'provenance.json', '模型、控制设置与源码核查边界')} · {link(ROOT / 'experiments/goal_progress_20261005/index.html', '此前完整阶段报告')}</p>
<details><summary>复现与工程检查</summary><p>本轮没有下载新模型或数据集；使用已有本地权重，推理启用离线模式。
新权重与数据只允许从中国大陆镜像或本土服务下载。生成式伙伴与 Genesis 在 GPU 0，OpenPI 在 GPU 1，各进程只使用单卡并在启动前检查显存。</p>
<p>测试覆盖视频失败门槛、真实接触贡献、控制限速、人体释放跳变和伙伴自消息反馈。完整命令与后续接触接口见项目 README。
这组联合运行的源码 SHA256 属于报告时文件快照；运行中新增了监测字段，因此不能把它当作精确的已执行源码证据。后续入口已经在运行前捕获源码并记录变化。</p></details>
<p class="quiet">生成时间：{stamp}。本页从保存的结果重建，不重新评分。研究目标尚未完成。</p></section></main></body></html>'''
    (HERE / "index.html").write_text(document, encoding="utf-8")
    sources = [NATIVE / "summary.json", NATIVE / "provenance.json", NATIVE / "video_verification.json",
               CALIBRATION / "summary.json", CALIBRATION / "video_verification.json"]
    (HERE / "evidence.json").write_text(json.dumps({"generated_at": stamp, "episodes": evidence,
        "source_sha256": {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in sources},
        "status": "diagnostic_only", "goal_complete": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(HERE / "index.html")


if __name__ == "__main__":
    main()
