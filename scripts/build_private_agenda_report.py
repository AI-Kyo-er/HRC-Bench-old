#!/usr/bin/env python3
"""双阶段人策略报告：目的、依赖、私人理解与真实动作，终态视频才发布。"""
import csv
from html import escape
import json
import os
from pathlib import Path

from build_coherent_batch_report import TASKS,SITUATIONS,render_findings
from hrc_pilot.joint_video_captions import ensure_research_captions
from hrc_pilot.joint_episode_inspection import render_inspection_panel
from hrc_pilot.reviewed_coordination_metrics import render_reviewed_metrics


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def build():
    output=Path('experiments/private_agenda_joint_20261008');results=Path('results/continuous_v2')
    def link(path,label):return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    cards=[];statuses=[]
    for row in csv.DictReader((output/'conditions.csv').open()):
        root=results/row['run'];ep=root/'episode';failure=read(root/'failure.json')
        verified=(read(root/'interaction_verification.json').get('status')=='verified' and
                  read(root/'independent_video_verification.json').get('status')=='verified')
        state='完整终态已核查' if verified else '失败，保留原始诊断' if failure else '尚无完整终态核查'
        title,dependency=TASKS[row['activity']];situation,question=SITUATIONS[row['situation']]
        card='<section><h2>'+escape(title+' · '+situation)+'</h2><p>'+escape(question)+'</p><p>可能贡献与依赖：'+escape(dependency)+'。具体安排由双方公开表达及实际贡献形成。</p><p>'+state+'；init'+row['init_state_id']+'，seed'+row['seed']+'，人物'+row['profile']+'。</p>'
        if verified:
            caption=ensure_research_captions(root);audit=read(root/'interaction_verification.json')
            card+='<p>人真实神经推理'+str(audit['human_neural_calls'])+'次；私人意图解析错误'+str(audit.get('human_private_agenda_parse_errors','未测量'))+'；真实VLA调用'+str(audit['robot_actual_vla_calls'])+'次。核验通过不是可信人物或协作成绩。</p>'
            card+='<video controls playsinline preload="none" src="'+escape(os.path.relpath(ep/'demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(caption,output),quote=True)+'"></video>'
            card+=render_inspection_panel(root,output)
            review=read(root/'public_request_response_review.json')
            card+='<p>'+escape(review.get('interpretation','私人需要如何兑现、双方如何继续或重组活动尚待逐例审阅。'))+'</p>'+render_findings(root,review)
            card+=render_reviewed_metrics(root)
            card+='<p>'+' · '.join(link(root/f,label) for f,label in [('provenance.json','设置与源码'),('interaction_verification.json','两阶段输入与控制核查'),('joint_process_evidence.json','实际过程证据'),('independent_video_verification.json','完整视频核查')])+'</p>'
            io=[json.loads(line) for line in (ep/'human_policy_io.jsonl').read_text().splitlines() if line.strip()]
            records=[]
            for decision in io:
                agenda=decision['private_agenda_inference']['agenda_after'] or {}
                records.append('<tr><td>'+str(decision['time_s'])+'</td><td>'+escape(agenda.get('current_need','未成功生成'))+'</td><td>'+escape(agenda.get('update_reason',''))+'</td><td>'+escape(decision['choice']['action'])+'</td><td>'+escape(decision['choice'].get('message',''))+'</td></tr>')
            card+='<details><summary>私人需要、更新依据与当前贡献：模型解释不是执行事实</summary><div class="scroll"><table><tr><th>模拟秒</th><th>自生成需要</th><th>自述更新依据</th><th>选定动作</th><th>实际公开表达</th></tr>'+''.join(records)+'</table></div></details>'
        else:card+='<p>不展示未结束视频作为结果。第一阶段的需要与第二阶段动作是否一致，必须结合完整环境与伙伴反馈判断。</p>'
        cards.append(card+'</section>');statuses.append({'condition':row,'state':state,'verified_terminal':verified,'formal_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>持续私人意图与当前贡献：跨活动资格检查</title><style>*{box-sizing:border-box}body{background:#edf3f1;color:#183c42;font:17px/1.7 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:24px 16px}section,header{padding:24px;background:white;border-radius:14px;margin:20px 0}header{background:#193d45;color:white}video{width:100%;background:#142d34}p,td,h2{overflow-wrap:anywhere}a{color:#13786e}.scroll{overflow-x:auto}table{min-width:700px;width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #cdd;text-align:left}@media(max-width:600px){main{padding:12px}section,header{padding:16px}}</style><main><header><h1>人的持续需要，如何变成当刻贡献</h1><p>三活动、同一生成式人方法。先生成私人理解，再依据实际世界选择贡献；正式样本0。</p></header><section><h2>实验目的、设置与边界</h2><p>当前单次推理方法已有完整观测，却仍出现说等待并开始搬运等不一致。新方法把持续私人需要、参与偏好、未解决事项和对约定的理解与当前贡献分开生成；两阶段均真实调用同一Qwen3-14B，后台不从需要或阶段标签选择动作。</p><p>当前场景完整保留；历史组织保留过去的需要、公开交流、真实执行的坐标、接触及持物，不重复整张旧关系矩阵。原始观测全部保存。私人理解不是世界事实，也不直接提供给机器人。</p><p>人执行沿用连续0.2m/s运动学附着；机器人为理想感知Qwen3-14B协调＋实际π0.5原生7D控制。额外退让语言仍未经能力资格；该限制保留。每条120模拟秒，一次世界初始化，每4模拟秒两次人推理、一次协调推理；模型墙钟耗时另存，不声称实时部署。</p><p>此页描述人策略架构资格检查，不把它充当第二个机器人模型、完整六情境覆盖或cobalance证明。需要评价真实贡献、伙伴反馈和共同活动的继续／重组，不能只数状态或对话。</p><p><a href="PROTOCOL.md">文献依据、两阶段逻辑与预定评价口径</a> · <a href="DESIGN_REVIEW.md">整批证据、任务缺口与下一步研究决定</a> · <a href="conditions.csv">运行前固定的三活动条件</a> · <a href="../relational_joint_20261008/index.html">此前关系动作与观测结果</a> · <a href="../joint_feasibility_20261007/index.html">统一历史与数据入口</a></p></section>'''+''.join(cards)+'</main></html>'
    page=page.replace('</style>','.inspection-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.episode-inspector{background:#f3f6fa;padding:16px;margin:12px 0;overflow-wrap:anywhere}select{max-width:100%;font:inherit}</style>')
    page=page.replace('</main></html>','</main><script src="../contract_joint_20261008/inspection.js"></script></html>')
    (output/'index.html').write_text(page)
    (output/'status.json').write_text(json.dumps({'role':'human_policy_architecture_development_status',
        'verified_terminal_cases':sum(s['verified_terminal'] for s in statuses),'conditions':statuses},ensure_ascii=False,indent=2))
    print(json.dumps({'conditions':len(statuses),'verified_terminal':sum(s['verified_terminal'] for s in statuses)}))


if __name__=='__main__':build()
