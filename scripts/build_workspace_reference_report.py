#!/usr/bin/env python3
"""新功能区的实际操作参考报告；不把固定调度当动态人策略。"""
import csv
from html import escape
import json
import os
from pathlib import Path

from hrc_pilot.joint_video_captions import ensure_research_captions
from hrc_pilot.workspace_contracts import WORKSPACE_CONTRACTS


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def build():
    output=Path('experiments/workspace_reference_20261008');cards=[];statuses=[]
    def link(path,label):return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    for row in csv.DictReader((output/'conditions.csv').open()):
        root=Path('results/continuous_v2')/row['run'];ep=root/'episode'
        audit=read(root/'interaction_verification.json');video=read(root/'independent_video_verification.json')
        verified=audit.get('status')=='verified' and video.get('status')=='verified'
        summary=read(root/'summary.json').get('episodes',[{}])[0]
        success=summary.get('reference_complete') if verified else None
        card='<section><h2>'+escape(WORKSPACE_CONTRACTS[row['activity']].activity.label)+'</h2>'
        card+='<p>init'+row['init_state_id']+'，seed'+row['seed']+'，预定120模拟秒。固定人准备／接收，Robot真实π0.5执行原生指令。</p>'
        if verified:
            captions=ensure_research_captions(root)
            card+='<video controls playsinline preload="none" src="'+escape(os.path.relpath(ep/'demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(captions,output),quote=True)+'"></video>'
            card+='<p>完整视频和输入／控制已核查；参考链'+('成立' if success else '未成立')+'。真实VLA调用'+str(audit['robot_actual_vla_calls'])+'次，人神经推理0次。参考等待和笛卡尔清场另标来源，不归功于π0.5协调能力。</p>'
            process=read(root/'joint_process_evidence.json');physical=process.get('original_arrangement_physical_observations',{})
            card+='<p>准备释放支撑首次见证：'+str(process.get('first_released_supported_preparation_s'))+'秒；原生操作首次稳定关系：'+str(summary.get('robot_native_goal_first_stable_s'))+'秒。操作结果与完整共同安排分别判断。</p>'
            if row['activity']=='drink_storage' and not success:
                card+='<p>人实际把酒瓶提供到新操作区，Robot没有完成上架，后续清盘参考因此未启动。这是当前模型在该新初态的操作失败；尚不能据单例证明不可达、位置是唯一原因或模型不具备HRC能力。</p>'
            card+='<p>'+' · '.join(link(root/name,label) for name,label in [
                ('summary.json','原始结果'),('workspace_layout.json','真实几何与功能区'),('provenance.json','模型和配置'),
                ('interaction_verification.json','输入／控制核查'),('joint_process_evidence.json','实际过程证据'),
                ('independent_video_verification.json','完整视频核查')])+'</p>'
        else:card+='<p>尚无完整核查；不展示未核查视频为最终结果。</p>'
        cards.append(card+'</section>');statuses.append({'condition':row,'verified_terminal':verified,
            'reference_complete':success,'formal_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>新功能区三活动操作资格</title><style>body{margin:0;background:#edf1f5;color:#182536;font:16px/1.7 system-ui}main{max-width:1100px;margin:auto;padding:24px}section{background:white;padding:22px;border-radius:12px;margin:18px 0}video{width:100%;max-height:600px;background:#10151b}a{color:#155aa7}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>新功能区：三活动真实Sim操作资格</h1><section><h2>目的、设置与解释范围</h2><p>新任务将准备、个人暂放和交付分开，并按各物品真实底部高度放置。12条初态的几何检查通过后，本批验证真实动作能否完成所需操作，避免把静态位置可用当作模型已能操作。</p><p>每例120模拟秒；固定人采用连续运动学附着，手速上限0.2m/s；Robot原生操作由π0.5真实7D动作执行。参考调度决定准备期保持与之后清场，不是动态人或生成式Robot协调策略；本批不计正式成绩。</p><p><a href="PROTOCOL.md">设置、参考控制边界和复现</a> · <a href="conditions.csv">预先固定的条件</a> · <a href="../contract_joint_20261008/index.html">此前动态人三活动完整结果</a> · <a href="../contract_joint_20261008/TASK_DESIGN_DECISIONS.md">任务设计与几何实现</a></p></section>'''+''.join(cards)+'</main></html>'
    page=page.replace('<a href="conditions.csv">预先固定的条件</a>', '<a href="conditions.csv">预先固定的条件</a> · <a href="PROVISION_CONTROL.md">饮品提供位置的独立控制与归因边界</a>')
    (output/'index.html').write_text(page)
    report={'role':'fixed_feasibility_reference_not_dynamic_policy',
        'verified_terminal':sum(row['verified_terminal'] for row in statuses),
        'reference_complete':sum(row['reference_complete'] is True for row in statuses),
        'formal_samples':0,'conditions':statuses}
    (output/'status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({key:report[key] for key in ['verified_terminal','reference_complete','formal_samples']}))


if __name__=='__main__':build()
