#!/usr/bin/env python3
"""独立可读的三活动报告；未核查完整视频不作为结果发布。"""
import csv
from html import escape
import json
import os
from pathlib import Path

from build_coherent_batch_report import SITUATIONS,render_findings
from hrc_pilot.interaction_contracts import CONTRACTS
from hrc_pilot.joint_video_captions import ensure_research_captions
from hrc_pilot.joint_episode_inspection import render_inspection_panel
from hrc_pilot.reviewed_coordination_metrics import render_reviewed_metrics


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def build(output=Path('experiments/contract_joint_20261008')):
    output=Path(output);contracts=CONTRACTS
    candidate=output.name=='candidate_joint_20261009'
    area_feedback=output.name=='area_feedback_20261009' or candidate
    workspace=output.name=='workspace_dynamic_20261008' or area_feedback
    if workspace:
        from hrc_pilot.workspace_contracts import WORKSPACE_CONTRACTS
        contracts=WORKSPACE_CONTRACTS
    def link(path,label):
        return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    cards=[];statuses=[]
    for row in csv.DictReader((output/'conditions.csv').open()):
        root=Path('results/continuous_v2')/row['run'];ep=root/'episode'
        contract=contracts[row['activity']];situation,question=SITUATIONS[row['situation']]
        audit=read(root/'interaction_verification.json');video=read(root/'independent_video_verification.json')
        verified=audit.get('status')=='verified' and video.get('status')=='verified'
        failure=read(root/'failure.json')
        status='完整运行与视频核查通过，协作有效性仍须逐例审阅' if verified else '运行失败，保留诊断' if failure else '尚无完整结果核查'
        card='<section><h2>'+escape(contract.activity.label+' · '+situation)+'</h2>'
        card+='<p>共同推进：'+escape(contract.jointly_organize)+'</p><p>本例问题：'+escape(question)+'</p>'
        card+='<p>人可能贡献：'+escape('；'.join(contract.human_contributions))+'。机器人可能贡献：'+escape('；'.join(contract.robot_contributions))+'。</p>'
        card+='<p>依赖：'+escape('；'.join(contract.activity.dependencies))+'。这些说明不是已接受的分工或动作顺序。</p>'
        card+='<p>'+escape(status)+'；init'+row['init_state_id']+'，seed'+row['seed']+'，人物'+row['profile']+'，预定120模拟秒。</p>'
        if verified:
            captions=ensure_research_captions(root)
            card+='<video controls playsinline preload="none" src="'+escape(os.path.relpath(ep/'demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(captions,output),quote=True)+'"></video>'
            card+=render_inspection_panel(root,output)
            card+='<p>真实人神经推理'+str(audit['human_neural_calls'])+'次；实际VLA调用'+str(audit['robot_actual_vla_calls'])+'次。核验覆盖输入和执行一致性，不等于人物可信或协作成功。</p>'
            review=read(root/'public_request_response_review.json')
            card+='<p>'+escape(review.get('interpretation','尚未完成逐例行为审阅；不将原生操作成绩作为共同活动成绩。'))+'</p>'+render_findings(root,review)
            card+=render_reviewed_metrics(root)
            choices=[json.loads(line) for line in (ep/'human_policy_io.jsonl').read_text().splitlines() if line.strip()]
            rows=[]
            for decision in choices:
                agenda=decision['private_agenda_inference']['agenda_after'] or {};choice=decision['choice']
                rows.append('<tr><td>'+str(decision['time_s'])+'</td><td>'+escape(agenda.get('current_need','未生成'))+'</td><td>'+escape(choice['action'])+'</td><td>'+escape(str(choice.get('object_id') or ''))+'</td><td>'+escape(str(choice.get('destination') or ''))+'</td><td>'+escape(choice.get('message') or '')+'</td></tr>')
            card+='<details><summary>人的需要、选定贡献与公开话语：不作为完成事实</summary><div class="scroll"><table><tr><th>模拟秒</th><th>私人需要</th><th>动作</th><th>对象</th><th>目标</th><th>公开话语</th></tr>'+''.join(rows)+'</table></div></details>'
            card+='<p>'+' · '.join(link(root/path,label) for path,label in [
                ('provenance.json','设置与源码'),('interaction_verification.json','实际输入与动作核查'),
                ('joint_process_evidence.json','实际过程证据'),('independent_video_verification.json','完整视频核查'),
                ('episode/public_dialogue.jsonl','双方实际公开交流'),('episode/trace.jsonl','完整环境轨迹')])+'</p>'
        else:
            card+='<p>未核查的运行不展示为完整实验视频，不计动态行为覆盖或正式样本。</p>'
        cards.append(card+'</section>')
        statuses.append({'condition':row,'verified_terminal':verified,'state':status,'formal_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>日常共同活动与动态伙伴：统一开发验证</title><style>body{margin:0;background:#edf1f5;color:#182536;font:16px/1.7 system-ui;overflow-wrap:anywhere}main{max-width:1100px;margin:auto;padding:24px}section{background:white;padding:22px;border-radius:12px;margin:18px 0}video{width:100%;max-height:600px;background:#10151b}a{color:#155aa7}.scroll{overflow:auto}table{border-collapse:collapse;min-width:760px}th,td{border:1px solid #d6dde5;padding:8px;vertical-align:top}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>日常共同活动与动态伙伴：统一开发验证</h1><section><h2>目的与设置</h2><p>此前双方能生成意图并操作物品，但尚未形成可靠的完整协作。本批重新组织共同任务与能力声明，检查人是否通过真实贡献和交流影响机器人，以及机器人能否据此调整行动。开发验证尚不构成正式Benchmark成绩。</p><p>人先生成持续私人需要，再依据实际场景选择当前贡献；机器人用公开几何、接触和对话独立决定操作，由π0.5真实生成机械臂动作。私人的意图不直接交给机器人。每条持续120模拟秒，不重置活动进度。人动作使用连续运动学附着，不声称真人手部接触动力学。</p><p>本批同时改变活动说明、能力菜单和可读场景关系，不作单因素改进结论。没有支撑关系、伙伴说完成或模型产生新意图，都不能单独证明活动结果或动态覆盖。</p><p><a href="PROTOCOL.md">任务依赖、私有与公开边界、评价及复现</a> · <a href="conditions.csv">运行前固定的三条条件</a> · <a href="../private_agenda_joint_20261008/DESIGN_REVIEW.md">此前整批失败与研究决定</a> · <a href="../joint_feasibility_20261007/index.html">统一进展与历史结果</a></p></section>'''+''.join(cards)+'</main></html>'
    geometry_root=Path('results/task_layout_review_20261008')
    if (geometry_root/'workspace_geometry.svg').is_file():
        figure_url=escape(os.path.relpath(geometry_root/'workspace_geometry.svg',output),quote=True)
        section='<section><h2>下一版布局设计：尚未运行新场景</h2><p>准备、个人暂放和交付位置已依据真实碰撞几何分开，12条保存初态的静态几何检查通过。该图不代表实际搬运、机器人可达或新的协作成功。</p>'
        section+='<img style="width:100%;max-width:650px" src="'+figure_url+'" alt="新功能区的桌面几何设计图，尚非实际执行轨迹">'
        section+='<p>'+link(geometry_root/'workspace_qualification.json','12条初态几何检查')+' · '+link(geometry_root/'initial_region_evidence.json','旧布局别名证据')+' · '+link(geometry_root/'workspace_geometry.svg','可导出的设计图')+'</p></section>'
        page=page.replace('</main>',section+'</main>')
    page=page.replace('<a href="conditions.csv">运行前固定的三条条件</a>', '<a href="conditions.csv">运行前固定的三条条件</a> · <a href="BATCH_REVIEW.md">整批结果、实际参与变化及下一版边界</a> · <a href="TASK_DESIGN_DECISIONS.md">任务依赖、布局证据与六情境设计决定</a>')
    if workspace:
        page=page.replace('日常共同活动与动态伙伴：统一开发验证','真实功能区与明确需要：六情境生成式伙伴开发')
        page=page.replace('运行前固定的三条条件','运行前固定的六条条件')
        page=page.replace('href="BATCH_REVIEW.md"','href="../contract_joint_20261008/BATCH_REVIEW.md"')
        page=page.replace('整批结果、实际参与变化及下一版边界','此前批次结果、实际参与变化及边界')
        page=page.replace('href="TASK_DESIGN_DECISIONS.md"','href="../contract_joint_20261008/TASK_DESIGN_DECISIONS.md"')
        page=page.replace('下一版布局设计：尚未运行新场景','本批使用的布局设计与静态资格')
        page=page.replace('该图不代表实际搬运、机器人可达或新的协作成功。','该图只说明静态布局；实际搬运和协作结果由各例视频及证据判断。')
        page=page.replace('<h2>目的与设置</h2>', '<h2>目的与设置</h2><p>六个配置覆盖三活动，实际行为覆盖须逐例核对。每4秒检查真实变化及20秒重新考虑决定是否调用NN；调度不选择动作。Robot读取公开需要与场景，私人用途只由人自己选择公开。</p>')
        page=page.replace('<a href="PROTOCOL.md">','<a href="OBSERVATION_NOTES.md">案例审阅与运行中原始证据</a> · <a href="PROTOCOL.md">')
        page=page.replace('<a href="OBSERVATION_NOTES.md">','<a href="BATCH_REVIEW.md">本批六例完整结果与下一步决定</a> · <a href="OBSERVATION_NOTES.md">')
        page=page.replace('<a href="conditions.csv">','<a href="COMPOSITION_DESIGN.md">交互结构及匹配对照设计（待实施）</a> · <a href="conditions.csv">')
    if area_feedback:
        page=page.replace('真实功能区与明确需要：六情境生成式伙伴开发','区域摆放与贡献事实：三活动联合验证')
        page=page.replace('运行前固定的六条条件','运行前固定的三条资格条件')
        page=page.replace('本批六例完整结果与下一步决定','本批三活动审阅与下一步决定')
        page=page.replace('六个配置覆盖三活动，实际行为覆盖须逐例核对。','三条条件验证同一区域内多物品分开放置及自身贡献事实反馈；这是联合方法资格，不是单因素改进或正式成绩。')
        page=page.replace('本批重新组织共同任务与能力声明，检查人是否通过真实贡献和交流影响机器人，以及机器人能否据此调整行动。','本批沿用此前共同任务和能力声明，增加交付区域内可分开放置的表达，以及与人自己选定贡献关联的当前事实。检查这些表达能否在真实决策中兑现，同时继续核对双方分工与动态行为。')
        page=page.replace('本批同时改变活动说明、能力菜单和可读场景关系，不作单因素改进结论。','本批同时增加区域放置与自身贡献事实反馈，并使用新的随机种子，不作单因素或因果改进结论。')
        page=page.replace('href="COMPOSITION_DESIGN.md"','href="../workspace_dynamic_20261008/COMPOSITION_DESIGN.md"')
        page=page.replace('<a href="PROTOCOL.md">','<a href="HUMAN_MODEL_CANDIDATE.md">下一版伙伴候选（尚无策略成绩）</a> · <a href="PROTOCOL.md">')
        page=page.replace('<h2>本批使用的布局设计与静态资格</h2>', '<h2>继承中心位置与静态资格</h2><p>图只显示原中心位置，不画本批扩展的交付中心范围；区域边界和当前占用的实际求解见各例workspace_layout和执行回执。</p>')
    if candidate:
        page=page.replace('区域摆放与贡献事实：三活动联合验证','候选生成式伙伴与v5：三活动真实闭环')
        page=page.replace('三条条件验证同一区域内多物品分开放置及自身贡献事实反馈；这是联合方法资格，不是单因素改进或正式成绩。',
                          '三条同初始化、同种子的条件检验候选32B与v5在实际执行、反馈和交流中的表现；人和文字协调器都换模型，不作单因素效果或正式成绩。')
        page=page.replace('本批同时增加区域放置与自身贡献事实反馈，并使用新的随机种子，不作单因素或因果改进结论。',
                          '本批沿用此前三条的种子、布局及能力，同时改变人/协调模型、加载精度及v5事实观测。接口通过不证明伙伴拟真，原生操作关系也不自动归机器人贡献。')
        page=page.replace('href="HUMAN_MODEL_CANDIDATE.md"','href="../area_feedback_20261009/HUMAN_MODEL_CANDIDATE.md"')
        page=page.replace('下一版伙伴候选（尚无策略成绩）','候选准备与尚未取得资格的边界')
        prefix_review=('<section><h2>运行中前缀审阅：尚非完整结果</h2>'
            '<p>首例点心的0至64模拟秒记录已审阅。20秒食品已经离手并由碗支撑；36秒装好的碗已离手进入交付区。'
            '这些是人的实际贡献，不能据此认定机器人完成摆盘或双方协作成功。</p>'
            '<p>32秒人说任务完成时实际仍持碗下放；机器人随后持续等待已经公开表达的确认。'
            '60秒双方说要将酒瓶移到饮品准备区，机器人实际选中的却是放酒架操作，当前九项操作没有相应自由区域目标。'
            '因此需要区分事实误记、约定更新失败、接口能力不匹配与具身执行失败。</p>'
            '<p>这是有原始锚点的助手审阅，未完成独立语义认证；不替代最终轨迹和完整视频核查。'
            '<a href="OBSERVATION_NOTES.md">33条原始来源及逐时刻解释</a> · '
            '<a href="CAPABILITY_REVIEW.md">共同任务与实际能力的设计决定</a> · '
            '<a href="../dynamic_joint_activity_20261007/DESIGN.md">完整Benchmark流程、模型适配及七项未完成要求</a></p></section>')
        page=page.replace('</main>',prefix_review+'</main>')
    page=page.replace('</style>','.inspection-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.episode-inspector{background:#f3f6fa;padding:16px;margin:12px 0;overflow-wrap:anywhere}select{max-width:100%;font:inherit}</style>')
    inspector='../contract_joint_20261008/inspection.js' if workspace else 'inspection.js'
    page=page.replace('</main></html>','</main><script src="'+inspector+'"></script></html>')
    (output/'index.html').write_text(page)
    result={'role':'unified_task_and_interaction_development',
        'verified_terminal_cases':sum(s['verified_terminal'] for s in statuses),
        'formal_samples':0,'conditions':statuses}
    (output/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'conditions':len(statuses),'verified_terminal':result['verified_terminal_cases']}))


if __name__=='__main__':build()
