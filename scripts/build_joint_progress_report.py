#!/usr/bin/env python3
"""从保存的实验与独立核查构建共同活动报告；未完成运行不当作结果。"""
import argparse
import csv
from html import escape
import json
import os
from pathlib import Path

from hrc_pilot.joint_video_captions import ensure_research_captions


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
    ('joint_skill_bank_snack_detour_20261008', '点心：临时饮品需要、可选技能库', 'neural'),
    ('joint_skill_bank_drink_correction_20261008', '饮品：具体用途纠正、可选技能库', 'neural'),
    ('joint_skill_bank_drawer_request_20261008', '抽屉：机器人请求、视觉技能库', 'neural'),
    ('joint_buffered_drawer_request_20261008', '抽屉：已选人贡献的连续暂放执行', 'neural'),
    ('joint_semantic_drawer_request_20261008', '抽屉：人意图语义观测与执行反馈', 'neural'),
    ('joint_semantic_drink_detour_20261008', '饮品：人意图语义观测与临时需要', 'neural'),
    ('joint_contribution_snack_change_use_20261008', '点心：人贡献参数语义与用途变化', 'neural'),
    ('joint_contribution_drink_detour_20261008', '饮品：人贡献参数语义与临时需要', 'neural'),
    ('joint_reasoning_drawer_request_20261008', '抽屉：人策略原生推理资格检查', 'neural'),
    ('joint_reasoning_snack_join_20261008', '点心：原生推理与实际加入资格', 'neural'),
    ('joint_reasoning_drink_correction_20261008', '饮品：原生推理与用途纠正资格', 'neural'),
    ('joint_tool_drink_correction_20261008', '饮品：原生工具严格话语接口诊断', 'neural'),
    ('joint_structured_tool_drink_correction_20261008', '饮品：完整工具反馈与用途纠正', 'neural'),
    ('joint_structured_tool_snack_join_symbolic_20261008', '点心：忙碌伙伴加入与理想测量协调', 'neural'),
    ('joint_natural_drink_correction_20261008', '饮品：自然贡献／交流与真实柜顶目标', 'neural'),
    ('joint_natural_drawer_leave_return_20261008', '抽屉：自然贡献接口的暂离返回', 'neural'),
    ('joint_constrained_drink_correction_20261008', '饮品：结构约束与明确暂停的资格检查', 'neural'),
    ('joint_constrained_drawer_leave_return_20261008', '抽屉：结构约束与参与变化的资格检查', 'neural'),
    ('joint_matched_reference_snack_service_init2_20261008', '点心：init2匹配原生操作参考', 'reference'),
    ('joint_matched_reference_drink_storage_init2_20261008', '饮品：init2匹配原生操作参考', 'reference'),
    ('joint_matched_reference_drawer_access_init2_20261008', '抽屉：init2匹配原生操作参考', 'reference'),
    ('joint_reference_snack_service_init4_20261008', '点心：init4原生操作参考', 'reference'),
    ('joint_reference_drink_storage_init4_20261008', '饮品：init4原生操作参考', 'reference'),
    ('joint_reference_drawer_access_init4_20261008', '抽屉：init4原生操作参考', 'reference'),
    ('joint_reference_snack_service_init5_20261008', '点心：init5原生操作参考', 'reference'),
    ('joint_reference_drink_storage_init5_20261008', '饮品：init5原生操作参考', 'reference'),
    ('joint_reference_drawer_access_init5_20261008', '抽屉：init5原生操作参考', 'reference'),
    ('joint_feasibility_snack_service_20261007', '点心：载荷接口崩溃', 'diagnostic'),
    ('joint_feasibility_drink_storage_20261007', '饮品：原固定人失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_handoff_20261007', '饮品：持物初态失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_replay_20261007', '饮品：开环回放失败', 'diagnostic'),
    ('joint_feasibility_drink_storage_tracking_20261007', '饮品：严格跟随失败', 'diagnostic'),
    ('relation_execution_init2_20261008','关系放置与真实VLA退让：init2资格检查','qualification'),
    ('relation_execution_init3_20261008','关系放置与真实VLA退让：init3资格检查','qualification'),
    ('relational_snack_detour_symbolic_20261008','关系贡献：点心偏离神经闭环开发','neural'),
    ('complete_observation_snack_detour_symbolic_20261008','完整公共观测：点心偏离神经闭环开发','neural'),
]
_coherent_table=Path('experiments/coherent_joint_20261008/conditions.csv')
if _coherent_table.exists():
    for _row in csv.DictReader(_coherent_table.open()):
        RUNS.append((_row['run'],f"一致开发批：{_row['activity']}／{_row['situation']}／{_row['system']}",'neural'))
_agenda_table=Path('experiments/private_agenda_joint_20261008/conditions.csv')
if _agenda_table.exists():
    for _row in csv.DictReader(_agenda_table.open()):
        RUNS.append((_row['run'],f"持续私人意图：{_row['activity']}／{_row['situation']}",'neural'))
_contract_table=Path('experiments/contract_joint_20261008/conditions.csv')
if _contract_table.exists():
    for _row in csv.DictReader(_contract_table.open()):
        RUNS.append((_row['run'],f"统一共同活动：{_row['activity']}／{_row['situation']}",'neural'))
_workspace_reference_table=Path('experiments/workspace_reference_20261008/conditions.csv')
if _workspace_reference_table.exists():
    for _row in csv.DictReader(_workspace_reference_table.open()):
        RUNS.append((_row['run'],f"新功能区操作资格：{_row['activity']}",'reference'))
RUNS.append(('workspace_drink_provision_control_20261008','饮品提供位置独立操作控制','reference'))
_workspace_dynamic_table=Path('experiments/workspace_dynamic_20261008/conditions.csv')
if _workspace_dynamic_table.exists():
    for _row in csv.DictReader(_workspace_dynamic_table.open()):
        RUNS.append((_row['run'],f"新功能区生成式伙伴：{_row['activity']}／{_row['situation']}",'neural'))
_area_feedback_table=Path('experiments/area_feedback_20261009/conditions.csv')
if _area_feedback_table.exists():
    for _row in csv.DictReader(_area_feedback_table.open()):
        RUNS.append((_row['run'],f"区域与贡献事实：{_row['activity']}／{_row['situation']}",'neural'))
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
        if summary and audit.get('status')!='verified':
            raise ValueError(f'{name} 完整结果尚无独立输入／执行核查，不能发布')
        process = read(root / 'joint_process_evidence.json')
        arrangement_review=read(root/'public_request_response_review.json')
        measured = process.get('measured_process', {})
        original_physical=process.get('original_arrangement_physical_observations',{})
        resources=process.get('shared_resource_execution',{})
        actual_contacts=resources.get('robot_gripper_contact_with_human_owned',{})
        contact_duration=actual_contacts.get('sampled_contact_duration_s')
        contact_label=f'{contact_duration:.2f}' if contact_duration is not None else '未测量'
        participation = measured.get('actual_participation', {})
        activity = provenance.get('activity', metrics.get('activity', 'snack_service'))
        task_label, dependency = TASKS[activity]
        if provenance.get('interaction_contract') or provenance.get('workspace_method'):
            from hrc_pilot.interaction_contracts import CONTRACTS
            if provenance.get('workspace_method'):
                from hrc_pilot.workspace_contracts import WORKSPACE_CONTRACTS
                CONTRACTS=WORKSPACE_CONTRACTS
            contract=CONTRACTS[activity]
            task_label=contract.activity.label
            dependency=contract.jointly_organize+'；'+'；'.join(contract.activity.dependencies)
        if kind=='qualification':
            task_label='关系执行与VLA操作检查'
            dependency='固定人放奶酪到碗、搬碗到盘；机器人实际VLA持续执行退让语言，非动态协调链。'
        duration = video['timeline']['benchmark_end_s']
        human_calls = audit.get('human_neural_calls', metrics.get('human_neural_calls', '未核查'))
        vla_calls = audit.get('robot_actual_vla_calls', '未核查')
        coordinator_calls = audit.get('robot_visual_coordinator_calls', '未核查')
        classification = {'reference':'可执行性参考','neural':'神经策略开发','diagnostic':'保留的失败诊断','qualification':'执行能力资格检查'}[kind]
        conclusion = ('完整参考链成立。固定人／参考调度不计动态策略成绩。'
                      if metrics.get('reference_complete') else
                      '参考链未完成。' if kind in {'diagnostic','reference'} and metrics else
                      '完整共同活动尚未验收；原生机器人目标只表示局部操作。')
        if failure: conclusion = '运行中断：' + failure['error'] + '。仅展示已录制部分，不计完整运行。'
        if kind=='qualification':
            conclusion='固定人关系动作及真实VLA操作资格检查。物理支撑与完整包含分开；退让指令响应不可靠。原生目标由人改变，不归功给机器人，也不计动态共同活动成绩。'
        if arrangement_review.get('neural_physical_chain_maintained'):
            conclusion='本例神经共同活动物理链成立并维持：机器人填装、人接收交付、双方随后保持。伙伴接口、动态加入及广覆盖仍需单独验收。'
        if arrangement_review.get('initial_storage_chain_physically_matched'):
            conclusion='初始存储成果有物理匹配：实际操作暂停后，人再请求打开、机器人执行、人存物。身体离返、通话时序、后续事实理解与完整动态协作验收分别判断。'
        if provenance.get('robot_replay_source'): conclusion += ' 当前机器人推理为零，不是 VLA 闭环成功。'
        if (root/'source_edit_note.json').exists(): conclusion += ' 存在已披露的运行期间文件编辑说明，仅作探索性证据。'
        links = [link(p,l) for p,l in [(root/'summary.json','结果'),(root/'failure.json','中断原因'),
            (root/'provenance.json','模型与设置'),(root/'interaction_verification.json','输入／执行核查'),
            (root/'joint_process_evidence.json','过程见证'),(root/'independent_video_verification.json','独立视频核查'),
            (ep/'human_policy_io.jsonl','人原始策略'),(ep/'robot_planner_io.jsonl','机器人协调推理'),
            (ep/'model_calls.jsonl','实际动作模型输入'),(ep/'trace.jsonl','真实环境轨迹'),
            (root/'source_edit_note.json','源文件说明')] if p.exists()]
        if arrangement_review:links.append(link(root/'public_request_response_review.json','当前公开请求与响应的实际证据'))
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
        caption=ensure_research_captions(root) if summary else None
        track=(f'<track kind="captions" srclang="zh-CN" label="研究者注释" default src="{escape(os.path.relpath(caption,output),quote=True)}">'
               if caption else '')
        details = f'<details><summary>策略选择与公开交流时间表（话语不等于执行）</summary><div class="scroll"><table><tr><th>模拟秒</th><th>主体</th><th>所选动作</th><th>实际公开话语</th></tr>{timeline}</table></div></details>'
        system=SYSTEMS.get(provenance.get('robot_system'), '失败运行未写入完整 provenance；见协议及中断日志')
        if provenance.get('robot_skill_bank'):system+='；NN从明确公开的原生操作库选择技能'
        cards.append(f'''<section class="run" data-kind="{kind}"><p class="tag">{classification} · {duration:.2f} 模拟秒</p>
<h2>{escape(label)}</h2><p>{escape(dependency)}</p><p>{escape(system)}。人策略来源：{escape(provenance.get('human_source','见协议'))}；原生推理：{provenance.get('human_thinking_enabled','未记录')}；额外反思：{provenance.get('human_reflection','未记录')}。</p>
<video controls playsinline preload="none" src="{src}">{track}</video><p>{escape(conclusion)}</p>
<p>{escape(arrangement_review.get('interpretation',''))}</p>
<p>原始安排的物理见证：首次满足 {original_physical.get('first_physical_match_s','未核查')} 秒；最后一秒持续满足 {original_physical.get('last_second_consistently_matches','未核查')}。
{escape(original_physical.get('scope','原始安排物理见证尚未重建；不据原生目标自动判断当前共同安排。'))}</p>
<p>实际人神经调用 {human_calls}；实际 VLA 调用 {vla_calls}；协调器调用 {coordinator_calls}。
机器人原生目标期末：{metrics.get('robot_native_goal_terminal','无完整终态')}。</p>
<p>实际身体离开区间：{escape(json.dumps(process.get('body_away_intervals',[]),ensure_ascii=False))}。
初始是否在旁边：{participation.get('initially_aside','尚未核查')}；后续实际离返周期：{escape(json.dumps(participation.get('departure_return_cycles',[]),ensure_ascii=False))}。
首次释放并支撑的准备位置见证：{process.get('first_released_supported_preparation_s','尚无')} 秒。
重复近目标搬运请求：{process.get('already_near_relocation_request_count','尚无')}；该计数不是重复劳动结论。</p>
<p>机器人所选保持时间：{measured.get('robot_selected_hold_duration_s','尚未核查')} 秒；已在目标的无运动请求满足：{measured.get('accepted_already_satisfied_request_count','尚未核查')}。
保持不自动等于无谓等待，动作请求完成不自动等于新增贡献。准备区域判据不穷尽所有合理准备方式。</p>
<p>同资源执行重叠：{resources.get('same_resource_vla_exposure_s','未重建')} 模拟秒；未识别技能的VLA控制步数：{resources.get('unmapped_vla_control_steps','未重建')}。
{escape(resources.get('scope','尚未重建，不能推断不存在冲突。'))}</p>
<p>夹爪与人持有／携带物品的采样接触：{contact_label} 模拟秒。
这是实际接触记录；不自动判定交接是否合法，也不证明人体碰撞或全身安全。</p>
<p>{' · '.join(links)}</p>{details}</section>''')
        data.append({'run':name,'label':label,'kind':kind,'activity':activity,'duration_s':duration,
                     'human_neural_calls':human_calls,'actual_vla_calls':vla_calls,'coordinator_calls':coordinator_calls,
                     'reference_complete':metrics.get('reference_complete'),'native_goal_terminal':metrics.get('robot_native_goal_terminal'),
                     'body_away_intervals':process.get('body_away_intervals',[]),'formal_benchmark_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>动态共同活动：可执行性与神经策略进展</title><style>*{box-sizing:border-box}body{margin:0;background:#edf3f1;color:#183c42;font:17px/1.75 system-ui}main{max-width:1100px;margin:auto;padding:24px 16px}header{background:#193d45;color:white;padding:28px;border-radius:16px}section{margin:20px 0;background:white;padding:24px;border-radius:14px}video{width:100%;background:#142d34;border-radius:8px}a{color:#13786e}h1,h2,p,a{overflow-wrap:anywhere}.tag{color:#6e4b15}.scroll{overflow-x:auto}table{width:100%;min-width:700px;border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #d1dfd8}button{margin:4px;padding:9px 14px;border:1px solid #13786e;border-radius:6px;background:#fff;color:#193d45;cursor:pointer}@media(max-width:600px){main{padding:12px}section,header{padding:18px 14px}}</style>
<main><header><h1>动态共同活动：可执行性与神经策略进展</h1><p>人的拟真重点是意图、参与和伙伴响应。研究对象是双方如何组织共同活动。</p></header>
<section><h2>怎样观看视频</h2><p>完整真实Sim视频提供可关闭的同步研究字幕，分别显示人的选择、实际执行状态和机器人所选操作。给人的私人消息仅供研究者理解实验，机器人没有收到这些字幕；原视频与模型图像保持原样。字幕不依据自报完成判定成功。部分崩溃视频保留原片，不加完整运行字幕。</p></section>
<section><h2>这批实验要回答什么</h2><p>先确认双方能够在连续场景中贡献、交接和完成活动，再检查在线人策略与机器人是否利用实际交互调整行为。参考条件只回答任务能否执行；神经条件用于暴露策略、输入和执行问题。本批版本不同，尚未形成冻结的多模型统计评测。</p>
<p>三类活动在init2已有完整实际π0.5参考。早期init0饮品成功参考使用既有轨迹的OSC反馈跟随，当前推理为零，来源仍单列保留。神经策略的完整共同活动、六类实际动态覆盖与cobalance仍未验收。</p>
<p><a href="TEST_INITIALIZATION_REFERENCE_PROTOCOL_20261008.md">init4／5六条操作参考协议</a>：参考抓取／放置或打开由实际π0.5完成；人调度、机器人等待及完成后的清场控制另记来源，不能称整条参考轨迹均由VLA生成。六条参考不计正式动态样本。</p>
<p><a href="REASONING_HUMAN_PROTOCOL_20261008.md">原生推理人资格设置</a> · <a href="GROUNDED_CONTRIBUTION_PROTOCOL_20261008.md">跨活动加入／纠正与测量修复协议</a>。已结束的推理抽屉条件：首次存放后再次取出，结束仍持奶酪；84秒公开说已存好与实物不符。旧接口10次拒绝返回＋搬物，旧观测漏报抽屉底面支撑。后续批修复接口并单独记录，历史结果不倒改。</p>
<p><a href="NATIVE_TOOL_HUMAN_PROTOCOL_20261008.md">原生工具反馈机制</a> · <a href="STRUCTURED_TOOL_ACTIVITY_PROTOCOL_20261008.md">完整工具条件与新的加入初态</a>。工具返回报告真实进展，不将选择动作当完成。话语对象只转发模型原话；已放置物品的沉降由低层执行容差处理，不替人选择下一贡献。</p>
<p><a href="HUMAN_DECISION_PROTOCOL_20261008.md">自然贡献／交流与真实支持面协议</a>：人选择搬放、持有、参与位置及独立的接受／拒绝／请求／结束表达；搬放包含完整取放，不要求学手指步骤。柜顶从当前碰撞几何计算，不使用柜体中心。人的结束声明仍需与实物和伙伴回应核对。新条件终态核查前只列待回收。</p>
<p><a href="CONSTRAINED_DECISION_PROTOCOL_20261008.md">合法结构与明确暂停协议</a>：新的解码条件限制接口类型，不按任务进展选择策略；NN可主动停止自己的运动，但暂停不等于释放物品。新条件使用非thinking、1024生成token，与旧thinking条件的预算不同，不能作单因素改善结论。</p>
<p><a href="../coherent_joint_20261008/index.html">一致开发批：目的、设置与逐例结果</a> · <a href="../coherent_joint_20261008/PROTOCOL.md">协议</a> · <a href="../coherent_joint_20261008/conditions.csv">预定12条条件</a>：同一原生思考＋结构约束的人方法，能力目录与队友实际话语分开；两个系统在同条件下允许不同的人回应。每条终态自动独立核查，不将尚未运行的配置算行为覆盖或正式成绩。</p>
<p><a href="../relational_joint_20261008/index.html">关系贡献、请求状态与退让操作资格检查</a>：两种初始化的固定人实际支撑有证据；π0.5未适配的退让指令不可靠。新神经闭环另列开发条件，不与旧批合并正式样本。</p>
<p><a href="../private_agenda_joint_20261008/index.html">持续私人需要与当前贡献分开生成：三活动资格批</a>：两次真实神经推理，当前完整场景和紧凑历史分开保留。后台不从意图标签选动作，私人理解不直接传给机器人。未结束条件不计终态结果或正式样本。</p>
<p><a href="../contract_joint_20261008/index.html">日常共同活动、能力域与伙伴线索：统一开发验证</a>：重新区分原生操作、当前共同约定和私人用途；人取放菜单匹配实际可移动物体，公开关系摘要来自真实接触与几何。三条条件在运行前记录，未核查终态不计结果，仍非正式评测。</p>
<p><a href="../workspace_reference_20261008/index.html">新功能区三活动真实操作资格</a>：固定人／参考调度与实际π0.5；2条参考链成立，饮品上架失败保留。静态几何可用不表示模型能操作，不计动态人或正式系统成绩。</p>
<p><a href="../workspace_dynamic_20261008/index.html">明确需要与真实功能区：六情境生成式伙伴开发</a>：三活动、六条预先记录的情境配置，实际覆盖须审阅行为。饮品改变提供位置的独立参考仍未上架，两条失败都保留并区分基本操作与协调归因。</p>
<p><a href="../area_feedback_20261009/index.html">区域摆放与贡献事实：三活动联合验证</a>：针对同一区域多物品及完成误记，扩展交付区域表达并将自己所选贡献与实际观测关联。条件预定，效果须真实Sim验证；不以测试通过计伙伴资格或正式成绩。</p>
<p><a href="COORDINATION_REVIEW_GUIDE.md">共同安排、实际贡献和负担审阅手册</a>：目标一致、分工一致、实际执行一致分别核对；不以两方都说完成或目标到位代表cobalance。
<a href="../../results/joint_evaluation_preparation_20261008/candidate_conditions.csv">72条候选样本条件</a> · <a href="../../results/joint_evaluation_preparation_20261008/preparation.json">未冻结状态</a> · <a href="../../results/joint_evaluation_preparation_20261008/model_file_fingerprints.json">模型文件指纹</a>。候选条件和磁盘文件指纹不是正式结果，不追溯证明旧进程内存参数；正式执行样本目前为0。</p>
<p>六条init4／5参考已结束：点心与抽屉各两条成立，饮品两条未上架。新推理点心32.45秒曾形成成品交付的物理见证，但108秒又取回、终态仍持物；0.95秒就加入，早于19.5秒个人事务结束消息。新饮品37.5秒用途澄清后，人改变公开要求并实际移瓶，机器人仍选择上架。原始关系未成立与未遵循当前需要是不同问题。</p>
<p>完整工具＋理想测量协调的点心条件出现新的正例：27.8秒成品释放到交付区并维持至120秒，双方后续确认并保持。它说明神经共同活动物理链可以成立；人早期已选择active及三次未持物place错误，仍需按伙伴条件和情境覆盖分别审阅。完整工具饮品中“柜顶完成”的声明与终态table接触不符，不能据声明计成功。</p>
<p>人：Qwen3-14B 在线生成意图、当前贡献与公开话语，部分条件另做一次实际神经反思。执行使用连续运动学和物体附着，手速上限 0.2m/s。机器人：π0.5 在原生 MuJoCo／LIBERO 场景中输出 7 维 OSC，20Hz 执行，不吸附或改写机器人位姿。此批不是 Genesis 场景。</p>
<p>理想感知协调器得到公开几何／接触和真实执行历史；与人共享冻结权重，输入上下文与私有记忆分开。它是额外策略系统，不能归因于裸 VLA。等待与参考控制不计为 VLA 调用。</p>
<p><a href="PROTOCOL.md">参考与开发协议</a> · <a href="SYMBOLIC_PROTOCOL.md">理想感知协调系统边界</a> · <a href="CONTRACT_PROTOCOL_20261008.md">参与契约修复协议</a> · <a href="VISUAL_SYSTEM_PROTOCOL_20261008.md">第二视觉系统协议</a> · <a href="SKILL_BANK_PROTOCOL_20261008.md">可选技能与具体情境协议</a> · <a href="SITUATIONS.md">六类情境及证据要求</a> · <a href="BEHAVIOR_REVIEW.md">关键行为分析</a> · <a href="README.md">实际进展与复现</a> · <a href="../dynamic_joint_activity_20261007/DESIGN.md">整体设计与文献依据</a></p>
<p><a href="../../datasets/dynamic_joint_activity_dev_20261008/README.md">可加载的开发行为数据</a> · <a href="../../datasets/dynamic_joint_activity_dev_20261008/dataset_verification.json">全量数据核查与实际数量</a>：按同stem匹配，私有人记录不进入机器人输入。参考控制、失败和保持明确来源，不标为成功专家示范。</p><p><a href="EVALUATION_PLAN.md">正式评测计划与尚待满足的实际证据</a></p></section>
<section><h2>如何读视频和指标</h2><p>视频是实际运行时 Sim，不是轨迹动画。每段已经独立解码并核对时间轴。公开话语是伙伴可收到的信息；私有意图是研究视图。模型声称完成、消息进入输入、物体实际到位和完整协作成立是不同层次。</p><p>抽屉原生技能条件显示用途更新及实际取出，但仍有重复搬运和过时计划。旧暂离字段问题已修复，新运行有实际桌边离返；具体时间、未覆盖的纠正／请求和执行阻断见关键行为分析。饮品中机器人虽停止操作，回复仍在等待释放后上架，不能据保持推断已接受留用。</p>
<button data-filter="all">全部</button><button data-filter="reference">可执行性参考</button><button data-filter="qualification">执行能力资格</button><button data-filter="neural">神经策略开发</button><button data-filter="diagnostic">失败诊断</button></section>'''
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
