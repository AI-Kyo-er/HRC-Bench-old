#!/usr/bin/env python3
"""从保存的实验与独立核查构建共同活动报告；未完成运行不当作结果。"""
import argparse
from html import escape
import json
import os
from pathlib import Path


RUNS = [
    ('joint_feasibility_drawer_access_20261007', '抽屉：固定人参考', 'reference'),
    ('joint_feasibility_snack_service_handoff_20261007', '点心：固定人参考', 'reference'),
    ('joint_feasibility_drink_storage_tolerant_20261007', '饮品：轨迹反馈参考', 'reference'),
    ('joint_grounded_drawer_access_20261007', '抽屉：直接 VLA 开发', 'neural'),
    ('joint_grounded_coordinated_drawer_20261007', '抽屉：视觉协调开发', 'neural'),
    ('joint_symbolic_drawer_access_change_use_20261007', '抽屉：理想感知协调初版', 'neural'),
    ('joint_symbolic_snack_service_leave_return_20261007', '点心：理想感知协调初版', 'neural'),
    ('joint_native_skill_drawer_access_change_use_20261007', '抽屉：原生技能接口', 'neural'),
    ('joint_native_skill_snack_service_leave_return_20261007', '点心：原生技能接口', 'neural'),
    ('joint_participation_snack_join_20261007', '点心：中途加入开发', 'neural'),
    ('joint_participation_snack_leave_return_20261007', '点心：暂离返回开发', 'neural'),
    ('joint_presence_contract_snack_leave_return_20261008', '点心：参与契约修复、新初始化', 'neural'),
    ('joint_dynamic_drink_correction_20261008', '饮品：纠正情境、新初始化', 'neural'),
    ('joint_visual_native_snack_leave_return_20261008', '点心：视觉原生技能系统', 'neural'),
    ('joint_feasibility_snack_service_20261007', '点心：载荷接口崩溃', 'diagnostic'),
    ('joint_feasibility_drink_storage_20261007', '饮品：原固定人失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_handoff_20261007', '饮品：持物初态失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_replay_20261007', '饮品：开环回放失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_tracking_20261007', '饮品：严格跟随失败', 'diagnostic'),
]
TASKS = {
    'snack_service': ('点心准备', '人放下接收碗 → 机器人装入奶酪并释放 → 人接收或交付点心。'),
    'drink_storage': ('饮品整理', '人决定留用或收纳、提供酒瓶 → 机器人放上架 → 人确认并整理台面。'),
    'drawer_access': ('抽屉取用', '人清理入口 → 机器人打开中层抽屉 → 人收纳物品或公开修改用途。'),
}
SYSTEMS = {
    'direct_vla_public_dialogue': '直接 π0.5；相机、状态及实际公开话语',
    'visual_coordinator_plus_vla': 'Qwen3-VL 视觉协调＋π0.5；额外的神经协调能力',
    'symbolic_coordinator_plus_vla': 'Qwen3 理想几何／接触协调＋π0.5；额外感知与协调能力',
    'saved_actions_feasibility_reference': '已保存动作／轨迹反馈参考；当前机器人神经推理为零',
}


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def build(results, output):
    output.mkdir(parents=True, exist_ok=True)
    def link(path, label):
        return f'<a href="{escape(os.path.relpath(path, output), quote=True)}">{escape(label)}</a>'
    cards = []; pending = []; data = []
    for name, label, kind in RUNS:
        root = results / name; ep = root / 'episode'
        summary = read(root / 'summary.json'); failure = read(root / 'failure.json')
        if not summary and not failure:
            pending.append(label + '：尚无终态结果'); continue
        video = read(root / 'independent_video_verification.json')
        if video.get('status') != 'verified':
            raise ValueError(f'{name} 尚无独立完整视频核查，不能发布')
        provenance = read(root / 'provenance.json')
        metrics = summary.get('episodes', [{}])[0]
        audit = read(root / 'interaction_verification.json')
        process = read(root / 'joint_process_evidence.json')
        measured = process.get('measured_process', {})
        participation = measured.get('actual_participation', {})
        activity = provenance.get('activity', metrics.get('activity', 'snack_service'))
        task_label, dependency = TASKS[activity]
        duration = video['timeline']['benchmark_end_s']
        human_calls = audit.get('human_neural_calls', metrics.get('human_neural_calls', '未核查'))
        vla_calls = audit.get('robot_actual_vla_calls', '未核查')
        coordinator_calls = audit.get('robot_visual_coordinator_calls', '未核查')
        classification = {'reference':'可执行性参考','neural':'神经策略开发','diagnostic':'保留的失败诊断'}[kind]
        conclusion = ('完整参考链成立。固定人／参考调度不计动态策略成绩。'
                      if metrics.get('reference_complete') else
                      '参考链未完成。' if kind == 'diagnostic' and metrics else
                      '完整共同活动尚未验收；原生机器人目标只表示局部操作。')
        if failure: conclusion = '运行中断：' + failure['error'] + '。仅展示已录制部分，不计完整运行。'
        if provenance.get('robot_replay_source'): conclusion += ' 当前机器人推理为零，不是 VLA 闭环成功。'
        if (root/'source_edit_note.json').exists(): conclusion += ' 存在已披露的运行期间文件编辑说明，仅作探索性证据。'
        links = [link(p,l) for p,l in [(root/'summary.json','结果'),(root/'failure.json','中断原因'),
            (root/'provenance.json','模型与设置'),(root/'interaction_verification.json','输入／执行核查'),
            (root/'joint_process_evidence.json','过程见证'),(root/'independent_video_verification.json','独立视频核查'),
            (ep/'human_policy_io.jsonl','人原始策略'),(ep/'robot_planner_io.jsonl','机器人协调推理'),
            (ep/'model_calls.jsonl','实际动作模型输入'),(ep/'trace.jsonl','真实环境轨迹'),
            (root/'source_edit_note.json','源文件说明')] if p.exists()]
        human_rows = rows(ep/'human_policy_io.jsonl'); plans = rows(ep/'robot_planner_io.jsonl')
        events = []
        for h in human_rows:
            c = h['choice']
            if c.get('action') != 'wait' or c.get('presence_choice','keep') != 'keep':
                events.append((h['time_s'],'人',c.get('action',''),c.get('message','')))
        for p in plans:
            d=p['decision']; events.append((p['time_s'],'机器人',d['mode'],d.get('message','')))
        events.sort(key=lambda x:x[0])
        timeline = ''.join(f'<tr><td>{t:.1f}</td><td>{who}</td><td>{escape(action)}</td><td>{escape(message)}</td></tr>'
                           for t,who,action,message in events)
        src=escape(os.path.relpath(ep/'demo.mp4',output),quote=True)
        details = f'<details><summary>策略选择与公开交流时间表（话语不等于执行）</summary><div class="scroll"><table><tr><th>模拟秒</th><th>主体</th><th>所选动作</th><th>实际公开话语</th></tr>{timeline}</table></div></details>'
        system=SYSTEMS.get(provenance.get('robot_system'), '失败运行未写入完整 provenance；见协议及中断日志')
        cards.append(f'''<section class="run" data-kind="{kind}"><p class="tag">{classification} · {duration:.2f} 模拟秒</p>
<h2>{escape(label)}</h2><p>{escape(dependency)}</p><p>{escape(system)}。人策略来源：{escape(provenance.get('human_source','见协议'))}。</p>
<video controls playsinline preload="none" src="{src}"></video><p>{escape(conclusion)}</p>
<p>实际人神经调用 {human_calls}；实际 VLA 调用 {vla_calls}；协调器调用 {coordinator_calls}。
机器人原生目标期末：{metrics.get('robot_native_goal_terminal','无完整终态')}。</p>
<p>实际身体离开区间：{escape(json.dumps(process.get('body_away_intervals',[]),ensure_ascii=False))}。
初始是否在旁边：{participation.get('initially_aside','尚未核查')}；后续实际离返周期：{escape(json.dumps(participation.get('departure_return_cycles',[]),ensure_ascii=False))}。
首次释放并支撑的准备位置见证：{process.get('first_released_supported_preparation_s','尚无')} 秒。
重复近目标搬运请求：{process.get('already_near_relocation_request_count','尚无')}；该计数不是重复劳动结论。</p>
<p>机器人所选保持时间：{measured.get('robot_selected_hold_duration_s','尚未核查')} 秒；已在目标的无运动请求满足：{measured.get('accepted_already_satisfied_request_count','尚未核查')}。
保持不自动等于无谓等待，动作请求完成不自动等于新增贡献。准备区域判据不穷尽所有合理准备方式。</p>
<p>{' · '.join(links)}</p>{details}</section>''')
        data.append({'run':name,'label':label,'kind':kind,'activity':activity,'duration_s':duration,
                     'human_neural_calls':human_calls,'actual_vla_calls':vla_calls,'coordinator_calls':coordinator_calls,
                     'reference_complete':metrics.get('reference_complete'),'native_goal_terminal':metrics.get('robot_native_goal_terminal'),
                     'body_away_intervals':process.get('body_away_intervals',[]),'formal_benchmark_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>动态共同活动：可执行性与神经策略进展</title><style>*{box-sizing:border-box}body{margin:0;background:#edf3f1;color:#183c42;font:17px/1.75 system-ui}main{max-width:1100px;margin:auto;padding:24px 16px}header{background:#193d45;color:white;padding:28px;border-radius:16px}section{margin:20px 0;background:white;padding:24px;border-radius:14px}video{width:100%;background:#142d34;border-radius:8px}a{color:#13786e}h1,h2,p,a{overflow-wrap:anywhere}.tag{color:#6e4b15}.scroll{overflow-x:auto}table{width:100%;min-width:700px;border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #d1dfd8}button{margin:4px;padding:9px 14px;border:1px solid #13786e;border-radius:6px;background:#fff;color:#193d45;cursor:pointer}@media(max-width:600px){main{padding:12px}section,header{padding:18px 14px}}</style>
<main><header><h1>动态共同活动：可执行性与神经策略进展</h1><p>人的拟真重点是意图、参与和伙伴响应。研究对象是双方如何组织共同活动。</p></header>
<section><h2>这批实验要回答什么</h2><p>先确认双方能够在连续场景中贡献、交接和完成活动，再检查在线人策略与机器人是否利用实际交互调整行为。参考条件只回答任务能否执行；神经条件用于暴露策略、输入和执行问题。本批版本不同，尚未形成冻结的多模型统计评测。</p>
<p>三类活动已有完整参考：点心和抽屉的机器人操作由实际 π0.5 输出；饮品成功参考使用既有轨迹的 OSC 反馈跟随，当前机器人推理为零。神经策略的完整共同活动、六类实际动态覆盖与 cobalance 仍未验收。</p>
<p>人：Qwen3-14B 在线生成意图、当前贡献与公开话语，部分条件另做一次实际神经反思。执行使用连续运动学和物体附着，手速上限 0.2m/s。机器人：π0.5 在原生 MuJoCo／LIBERO 场景中输出 7 维 OSC，20Hz 执行，不吸附或改写机器人位姿。此批不是 Genesis 场景。</p>
<p>理想感知协调器得到公开几何／接触和真实执行历史；与人共享冻结权重，输入上下文与私有记忆分开。它是额外策略系统，不能归因于裸 VLA。等待与参考控制不计为 VLA 调用。</p>
<p><a href="PROTOCOL.md">参考与开发协议</a> · <a href="SYMBOLIC_PROTOCOL.md">理想感知协调系统边界</a> · <a href="CONTRACT_PROTOCOL_20261008.md">参与契约修复协议</a> · <a href="VISUAL_SYSTEM_PROTOCOL_20261008.md">第二视觉系统协议</a> · <a href="SITUATIONS.md">六类情境及证据要求</a> · <a href="BEHAVIOR_REVIEW.md">关键行为分析</a> · <a href="README.md">实际进展与复现</a> · <a href="../dynamic_joint_activity_20261007/DESIGN.md">整体设计与文献依据</a></p>
<p><a href="../../datasets/dynamic_joint_activity_dev_20261008/README.md">可加载的开发行为数据</a>：15条完整轨迹、5760组观测、36000步实际动作；按同stem匹配，私有人记录不进入机器人输入。参考控制、失败和保持明确来源，不标为成功专家示范。</p></section>
<section><h2>如何读视频和指标</h2><p>视频是实际运行时 Sim，不是轨迹动画。每段已经独立解码并核对时间轴。公开话语是伙伴可收到的信息；私有意图是研究视图。模型声称完成、消息进入输入、物体实际到位和完整协作成立是不同层次。</p><p>抽屉原生技能条件显示用途更新及实际取出，但仍有重复搬运和过时计划。暂离条件出现“说已离开、身体未离开”的接口问题，不能按话语计覆盖。具体时间及结论见关键行为分析。</p>
<button data-filter="all">全部</button><button data-filter="reference">可执行性参考</button><button data-filter="neural">神经策略开发</button><button data-filter="diagnostic">失败诊断</button></section>'''
    if pending:page+='<section><h2>尚无终态结果</h2><p>'+escape('；'.join(pending))+'。未完成运行不计入下方结果。</p></section>'
    page+=''.join(cards)+'''<section><h2>尚待完成的 Goal 要求</h2><p>六类情境的实际行为覆盖、经过验证的可靠动态伙伴、完整双向重组案例、多系统多初始化正式评测、共同约定与协调负担评价仍待完成。参考成功、局部原生目标和接口核查均不能替代这些要求。</p></section></main><script>for(const b of document.querySelectorAll('[data-filter]'))b.onclick=()=>{for(const s of document.querySelectorAll('.run'))s.hidden=b.dataset.filter!=='all'&&s.dataset.kind!==b.dataset.filter;};</script></html>'''
    (output/'index.html').write_text(page)
    (output/'results_index.json').write_text(json.dumps({'purpose':'报告索引，不编码训练数据配对','runs':data,'pending':pending},ensure_ascii=False,indent=2))
    print(json.dumps({'published_runs':len(data),'pending':pending},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path('results/continuous_v2'))
    parser.add_argument('--output-dir',type=Path,default=Path('experiments/joint_feasibility_20261007'))
    args=parser.parse_args();build(args.results_dir,args.output_dir)
