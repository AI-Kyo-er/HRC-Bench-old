#!/usr/bin/env python3
"""关系贡献与退让资格检查报告；真实结果和待完成神经条件分开。"""
import json
import os
from html import escape
from pathlib import Path

from hrc_pilot.joint_video_captions import ensure_research_captions
from build_coherent_batch_report import render_findings


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def build():
    output=Path('experiments/relational_joint_20261008');results=Path('results/continuous_v2')
    def link(path,label):return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    sections=[]
    for init in [2,3]:
        root=results/f'relation_execution_init{init}_20261008';ep=root/'episode'
        evidence=read(root/'relation_execution_evidence.json').get('summary',{})
        verified=(evidence.get('status')=='records_geometry_and_video_verified'
                  and read(root/'interaction_verification.json').get('status')=='verified'
                  and read(root/'independent_video_verification.json').get('status')=='verified')
        title=f'固定关系执行检查 · init{init} · seed{80+init}'
        if not verified:
            sections.append('<section><h2>'+title+'</h2><p>尚无完整核查结果，不发布终态结论。</p></section>');continue
        caption=ensure_research_captions(root)
        body='<section><h2>'+title+'</h2><p>完整60模拟秒；人NN=0，固定先放奶酪，再搬碗到盘上。机器人实际π0.5推理'+str(evidence['actual_vla_calls'])+'次、控制'+str(evidence['actual_robot_controls'])+'步，每次目标均为固定退让语言指令。无人协调决策；不计动态HRC成绩。</p>'
        body+='<video controls playsinline preload="none" src="'+escape(os.path.relpath(ep/'demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(caption,output),quote=True)+'"></video>'
        body+='<p>原始运行时Sim及两路模型相机。字幕独立提供人的选择与实际持物状态，不修改视频或策略输入。</p><div class="scroll"><table><tr><th>实际关系</th><th>解算中心面接触＋释放＋位置，最后1秒</th><th>参考物支撑＋释放，最后1秒</th><th>解释</th></tr>'
        for name,v in evidence['measured_relation_results'].items():
            bowl=name.startswith('akita');label='碗在盘上' if bowl else '奶酪与碗'
            explanation='盘面实际接触并保持。' if bowl else '奶酪由碗侧面支撑，不接触解算碗底；支撑不证明整个物品被容纳。'
            body+='<tr><td>'+label+'</td><td>'+('成立' if v['last_second_consistent'] else '未成立')+'</td><td>'+('成立' if v['last_second_released_reference_support'] else '未成立')+'</td><td>'+explanation+'</td></tr>'
        body+='</table></div><p>末端终态相对起点位移（米）：'+escape(str([round(x,3) for x in evidence['robot_eef_displacement_m']]))+'。init2大幅移离桌边，init3向下移动；这条未适配语言操作不具备可靠退让资格。末端位移也不能证明全机械臂清场。</p>'
        body+='<p>关系几何独立重建最大轴误差 '+str(evidence['relation_geometry_max_axis_error_m'])+' 米。选择、低层宏结束、真实接触及完整活动成功分别记录。</p><p>'+' · '.join(link(root/f,label) for f,label in [('relation_execution_evidence.json','完整物理与动作证据'),('interaction_verification.json','输入与控制核查'),('independent_video_verification.json','完整视频核查'),('provenance.json','模型设置与运行源码'),('research_caption_provenance.json','字幕来源')])+'</p></section>'
        sections.append(body)
    neural=results/'relational_snack_detour_symbolic_20261008'
    done=(read(neural/'interaction_verification.json').get('status')=='verified' and
          read(neural/'independent_video_verification.json').get('status')=='verified')
    if done:
        caption=ensure_research_captions(neural)
        review=read(neural/'public_request_response_review.json')
        sections.append('<section><h2>神经闭环：点心活动的临时偏离</h2><p>完整结果已经核查；动态行为及当前安排仍需逐例审阅，不能用运行结束认证。</p><video controls playsinline preload="none" src="'+escape(os.path.relpath(neural/'episode/demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(caption,output),quote=True)+'"></video><p>'+escape(review.get('interpretation','行为与当前安排尚待审阅。'))+'</p>'+render_findings(neural,review)+'<p>'+link(neural/'index.html','运行报告与数据')+' · '+link(neural/'interaction_verification.json','实际输入／控制核验')+' · '+link(neural/'joint_process_evidence.json','共同活动过程证据')+'</p></section>')
    else:
        sections.append('<section><h2>神经闭环：点心活动的临时偏离</h2><p>已启动开发诊断，尚无完整独立核查结果。init3/seed71，人Qwen3-14B，理想感知14B协调＋π0.5，120秒。人获得关系放置及明确执行状态；机器人可以选择退让语言操作，但其执行资格尚不成立。保留这项限制，不计正式样本或与旧接口混合比较。</p></section>')
    complete=results/'complete_observation_snack_detour_symbolic_20261008'
    complete_done=(read(complete/'interaction_verification.json').get('status')=='verified' and
                   read(complete/'independent_video_verification.json').get('status')=='verified')
    if complete_done:
        caption=ensure_research_captions(complete);review=read(complete/'public_request_response_review.json')
        sections.append('<section><h2>完整公共观测：点心活动闭环</h2><p>本例显式提供物体坐标、相对距离、接触及持物测量；不是给出正确下一动作。理想感知机器人也获得同一公共测量的表达，不能当只改变人输入的因果消融。</p><video controls playsinline preload="none" src="'+escape(os.path.relpath(complete/'episode/demo.mp4',output),quote=True)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+escape(os.path.relpath(caption,output),quote=True)+'"></video><p>'+escape(review.get('interpretation','完整行为及当前安排尚待审阅。'))+'</p>'+render_findings(complete,review)+'<p>'+link(complete/'index.html','运行报告与数据')+'</p></section>')
    else:
        sections.append('<section><h2>完整公共观测：已启动的后续闭环</h2><p>尚无完整独立核查结果，不发布部分视频或改进结论。保持init3/seed71、私有消息、策略提示词、动作接口和机器人操作库，补齐实际物体坐标、相对距离、接触及持物信息。人当前输入和历史执行反馈都保留这些测量；理想感知机器人也收到公共测量，视觉机器人和直接VLA接口没有偷加几何。结果不能归为单独人输入的因果效应，也不计正式成绩。</p></section>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>关系贡献与退让：实际能力资格检查</title><style>*{box-sizing:border-box}body{background:#edf3f1;color:#183c42;font:17px/1.7 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:24px 16px}section,header{padding:24px;background:white;border-radius:14px;margin:20px 0}header{background:#193d45;color:white}video{width:100%;background:#142d34}p,td,h2{overflow-wrap:anywhere}a{color:#13786e}.scroll{overflow-x:auto}table{min-width:650px;border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #cdd}@media(max-width:600px){main{padding:12px}section,header{padding:16px}}</style><main><header><h1>把人的用途选择兑现为实际贡献</h1><p>关系放置、执行状态与机器人退让能力分别验证；不是动态策略或cobalance成功报告。</p></header><section><h2>为什么做这次实验</h2><p>上一批12条开发发现：人说“放进碗”却只能选择个人桌面点，已完成请求仍像在执行，抽屉受阻时机器人没有独立退让选项。这些接口限制会污染HRC归因。</p><p>本轮在人可靠简化执行上增加对象—关系—参考物的目标，按当前实际碰撞面计算；明确正在执行与最近完成的请求。机器人退让只提供实际VLA语言操作，真实输出动作，绝不用参考清场替它完成。两条固定人参考用于资格检查，不能替代后续神经意图、参与与伙伴响应。</p><p>两种初始化均支持碗在盘上、奶酪随碗搬运后的释放支撑；奶酪不接触解算碗底。退让语言响应不可靠。完整Goal仍需六种实际行为、有效动态人物、持续重组、多初始化正式比较及人协调负担评价；正式样本0。</p><p><a href="PROTOCOL.md">目的、预定条件与启动决定</a> · <a href="OBSERVATION_REVIEW.md">必要观测的缺口与归因</a> · <a href="PERCEPTION_PROTOCOL.md">完整公共观测的接入与验证口径</a> · <a href="../../results/public_observation_contract_20261008/measurement_contract_verification.json">59条记录的观测重建核查</a> · <a href="../coherent_joint_20261008/BATCH_REVIEW.md">上一批完整诊断</a> · <a href="../joint_feasibility_20261007/index.html">统一历史与数据入口</a></p></section>'''+''.join(sections)+'</main></html>'
    output.mkdir(parents=True,exist_ok=True);(output/'index.html').write_text(page)
    print(json.dumps({'qualification_videos':sum('video controls' in s for s in sections[:2]),'neural_verified':done}))


if __name__=='__main__':build()
