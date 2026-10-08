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


def build():
    output=Path('experiments/contract_joint_20261008')
    def link(path,label):
        return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    cards=[];statuses=[]
    for row in csv.DictReader((output/'conditions.csv').open()):
        root=Path('results/continuous_v2')/row['run'];ep=root/'episode'
        contract=CONTRACTS[row['activity']];situation,question=SITUATIONS[row['situation']]
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
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>日常共同活动与动态伙伴：统一开发验证</title><style>body{margin:0;background:#edf1f5;color:#182536;font:16px/1.7 system-ui}main{max-width:1100px;margin:auto;padding:24px}section{background:white;padding:22px;border-radius:12px;margin:18px 0}video{width:100%;max-height:600px;background:#10151b}a{color:#155aa7}.scroll{overflow:auto}table{border-collapse:collapse;min-width:760px}th,td{border:1px solid #d6dde5;padding:8px;vertical-align:top}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>日常共同活动与动态伙伴：统一开发验证</h1><section><h2>目的与设置</h2><p>此前双方能生成意图并操作物品，但尚未形成可靠的完整协作。本批重新组织共同任务与能力声明，检查人是否通过真实贡献和交流影响机器人，以及机器人能否据此调整行动。开发验证尚不构成正式Benchmark成绩。</p><p>人先生成持续私人需要，再依据实际场景选择当前贡献；机器人用公开几何、接触和对话独立决定操作，由π0.5真实生成机械臂动作。私人的意图不直接交给机器人。每条持续120模拟秒，不重置活动进度。人动作使用连续运动学附着，不声称真人手部接触动力学。</p><p>本批同时改变活动说明、能力菜单和可读场景关系，不作单因素改进结论。没有支撑关系、伙伴说完成或模型产生新意图，都不能单独证明活动结果或动态覆盖。</p><p><a href="PROTOCOL.md">任务依赖、私有与公开边界、评价及复现</a> · <a href="conditions.csv">运行前固定的三条条件</a> · <a href="../private_agenda_joint_20261008/DESIGN_REVIEW.md">此前整批失败与研究决定</a> · <a href="../joint_feasibility_20261007/index.html">统一进展与历史结果</a></p></section>'''+''.join(cards)+'</main></html>'
    page=page.replace('</style>','.inspection-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.episode-inspector{background:#f3f6fa;padding:16px;margin:12px 0;overflow-wrap:anywhere}select{max-width:100%;font:inherit}</style>')
    page=page.replace('</main></html>','</main><script src="inspection.js"></script></html>')
    (output/'index.html').write_text(page)
    result={'role':'unified_task_and_interaction_development',
        'verified_terminal_cases':sum(s['verified_terminal'] for s in statuses),
        'formal_samples':0,'conditions':statuses}
    (output/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'conditions':len(statuses),'verified_terminal':result['verified_terminal_cases']}))


if __name__=='__main__':build()
