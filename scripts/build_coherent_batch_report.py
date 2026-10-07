#!/usr/bin/env python3
"""面向未参与工作流的读者说明一致开发批；只发布独立核验的终态视频。"""
import argparse
import csv
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path


TASKS={'snack_service':('点心准备','提供容器、填装点心、接收或交付'),
       'drink_storage':('饮品整理','公开决定留用或收纳、提供瓶子、放置并确认'),
       'drawer_access':('抽屉整理','清理入口、打开抽屉、存取或修改用途')}
SITUATIONS={
    'join':('中途加入','忙于个人事务的人何时开始承担贡献，机器人怎样重新安排？'),
    'detour':('临时偏离','先处理来客饮品需要，随后取消或恢复原活动，是否保留已有进度？'),
    'change_use':('用途变化','原来准备收纳的物品临时需要马上取用，双方能否更新目标与分工？'),
    'correction':('纠正与接管','澄清原用途误解后，谁实际修正、谁让权，是否仍有重复操作？'),
    'leave_return':('暂离返回','人处理中途联系，伙伴期间怎样工作，回来后是否衔接当前进度？'),
    'robot_request':('主动求助','机器人是否提出真实具体请求，人能接受、修改或拒绝并产生后果？')}


def read(path):return json.loads(path.read_text()) if path.exists() else {}
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def render_findings(root, review):
    """展现有原始证据的案例解释；锚点核对与语义判断保持区分。"""
    if not review.get('findings'):
        return ''
    verification=read(root/'review_evidence_verification.json')
    current=verification.get('status')=='evidence_anchors_verified'
    current=current and verification.get('review_sha256')==sha256((root/'public_request_response_review.json').read_bytes()).hexdigest()
    for name,digest in verification.get('source_sha256',{}).items():
        path=root/name
        current=current and path.is_file() and sha256(path.read_bytes()).hexdigest()==digest
    if not current:
        return '<p>案例解释的证据引用尚未核对或来源已变化，暂不展示详细判断。</p>'
    items=''.join('<li><strong>'+escape(finding.get('label','案例观察'))+'</strong>：'+
                  escape(finding['interpretation'])+'</li>' for finding in review['findings'])
    return ('<h3>这次实际发生了什么</h3><ul>'+items+
            '</ul><p>以上为助手对保存记录的解释；引用已核对，不代表独立专家评分或真人验证。</p>')


def case_state(root):
    summary=read(root/'summary.json');failure=read(root/'failure.json')
    if failure:return '运行失败，保留诊断',False
    if not summary:return ('尚无终态结果' if root.exists() else '尚未启动'),False
    verified=(read(root/'interaction_verification.json').get('status')=='verified' and
              read(root/'independent_video_verification.json').get('status')=='verified')
    return ('完整终态已独立核验' if verified else '已结束，等待独立核验'),verified


def build(table,results,output):
    output.mkdir(parents=True,exist_ok=True);conditions=list(csv.DictReader(table.open()))
    def link(path,label):return f'<a href="{escape(os.path.relpath(path,output),quote=True)}">{escape(label)}</a>'
    cards=[];states=[]
    for condition in conditions:
        root=results/condition['run'];ep=root/'episode';state,verified=case_state(root)
        title,steps=TASKS[condition['activity']];situation,question=SITUATIONS[condition['situation']]
        system='视觉8B协调＋π0.5' if condition['system']=='visual' else '理想感知14B协调＋π0.5'
        html=f'<section><h2>{escape(title)} · {escape(situation)} · {escape(system)}</h2><p>{escape(question)}</p>'
        html+=f'<p>{escape(state)}。初态编号 {condition["init_state_id"]}，seed {condition["seed"]}，人物 {condition["profile"]}；初始持物：{condition["initial_human_holding"]=="1"}。共同贡献：{escape(steps)}。</p>'
        if verified:
            video=os.path.relpath(ep/'demo.mp4',output)
            html+=f'<video controls playsinline preload="none" src="{escape(video,quote=True)}"></video>'
            audit=read(root/'interaction_verification.json');process=read(root/'joint_process_evidence.json')
            review=read(root/'public_request_response_review.json')
            html+=f'<p>实际人NN {audit.get("human_neural_calls")}，协调NN {audit.get("robot_visual_coordinator_calls")}，VLA调用 {audit.get("robot_actual_vla_calls")}。同资源执行重叠 {process.get("shared_resource_execution",{}).get("same_resource_vla_exposure_s","未测量")} 模拟秒。</p>'
            contact=process.get('shared_resource_execution',{}).get('robot_gripper_contact_with_human_owned',{})
            duration=contact.get('sampled_contact_duration_s')
            label=f'{duration:.2f}' if duration is not None else '未测量'
            html+=f'<p>夹爪与人持有／携带物品的采样接触时间：{label} 模拟秒。接触和技能执行重叠分别测量；合法交接、人体碰撞及安全性需另外判断。</p>'
            html+='<p>'+escape(review.get('interpretation','场景行为与当前安排尚待语义审阅；核验通过只证明输入和执行可重建。'))+'</p>'
            html+=render_findings(root,review)
            html+='<p>'+' · '.join(link(p,label) for p,label in [
                (root/'provenance.json','设置与版本'),(root/'interaction_verification.json','输入／控制核验'),
                (root/'joint_process_evidence.json','过程证据'),(root/'independent_video_verification.json','视频核验'),
                (root/'public_request_response_review.json','行为与安排审阅'),
                (root/'review_evidence_verification.json','解释引用核对')] if p.exists())+'</p>'
            messages=rows(ep/'public_dialogue.jsonl')
            timeline=''.join(f'<tr><td>{m["time_s"]:.1f}</td><td>{escape(m["speaker"])}</td><td>{escape(m["text"])}</td></tr>'
                             for m in messages if m['speaker'] in {'human','robot'})
            html+='<details><summary>实际公开交流时间表：话语不是完成事实</summary><div class="scroll"><table><tr><th>模拟秒</th><th>主体</th><th>原话</th></tr>'+timeline+'</table></div></details>'
        html+='</section>';cards.append(html)
        states.append({'condition':condition,'state':state,'verified_terminal':verified,'formal_sample':False})
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>动态共同活动：一致方法的六情境开发批</title><style>*{box-sizing:border-box}body{margin:0;background:#edf3f1;color:#183c42;font:17px/1.7 system-ui}main{max-width:1100px;margin:auto;padding:24px 16px}section,header{background:white;padding:24px;border-radius:14px;margin:20px 0}header{background:#193d45;color:white}video{width:100%;background:#142d34}a{color:#13786e}p,h1,h2,td{overflow-wrap:anywhere}.scroll{overflow-x:auto}table{width:100%;min-width:650px}td,th{padding:8px;text-align:left;border-bottom:1px solid #d1dfd8}@media(max-width:600px){main{padding:12px}section,header{padding:16px}}</style><main>
    <header><h1>三活动、六情境：同一伙伴方法的闭环开发批</h1><p>研究对象是双方如何组织并调整共同活动。12条预定条件，不是12条已经成功的情境。</p></header>
    <section><h2>实验目的与设置</h2><p>前期已证明神经策略可以完成点心共同活动物理链，但人会误解需求、声明未发生的完成，或与机器人同时搬同一物品。本批固定同一人方法，扩大到日常参与与意图变化，检验伙伴有效性、场景覆盖和协调过程。</p>
    <p>人：Qwen3-14B依据个人需要、实际测量、公开互动和自选记忆作决策；原生思考后约束调用格式。思考不是教师策略，合法格式不保证理解正确。执行为连续运动学附着，0.2m/s。机器人：π0.5在原生MuJoCo/LIBERO输出7D动作，20Hz控制，不吸附或改写机器人位姿。协调每4秒更新。</p>
    <p>页面和视频中的事件时刻为模拟时间。4秒决策间隔不代表模型能在真实墙钟4秒内完成推理；推理墙钟成本另外保存，本批不能证明实时部署能力。</p>
    <p>两个系统在同一条件下使用相同初始化、人物、外部事实和seed，但人可以因机器人行为不同产生不同回应。视觉与理想感知系统同时改变感知和模型，这不是单因素消融或裸VLA排名。</p>
    <p>不强迫每例加入、变心、离开或求助。人的私有意图不直接提供给机器人；只转发实际公开表达和可见行为。环境能力目录不当作队友请求。动作接受、目标到位和双方接受安排分别审阅。</p>
    <p><a href="PROTOCOL.md">完整协议</a> · <a href="conditions.csv">运行前固定的12条条件</a> · <a href="REFERENCE_DECISIONS.md">文献设计与当前缺口</a> · <a href="../joint_feasibility_20261007/COORDINATION_REVIEW_GUIDE.md">协调证据口径</a> · <a href="../joint_feasibility_20261007/index.html">全部历史结果与失败</a></p></section>'''
    page+=''.join(cards)+'''<section><h2>结论边界</h2><p>当前正式评测样本为0。任务配置、神经话语、类型校验及物理关系均不能代替六类实际变化、可靠伙伴、有效分工重组或cobalance。每条未发生/失败条件保留在预定分母，后续根据具体案例判断是否进入正式多初始化评测。</p></section></main></html>'''
    (output/'index.html').write_text(page)
    (output/'status.json').write_text(json.dumps({'role':'development_status_not_training_pairs',
        'conditions':states,'verified_terminal_cases':sum(s['verified_terminal'] for s in states)},ensure_ascii=False,indent=2))
    print(json.dumps({'conditions':len(states),'verified_terminal':sum(s['verified_terminal'] for s in states)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table',type=Path,default=Path('experiments/coherent_joint_20261008/conditions.csv'))
    parser.add_argument('--results-dir',type=Path,default=Path('results/continuous_v2'))
    parser.add_argument('--output-dir',type=Path,default=Path('experiments/coherent_joint_20261008'))
    args=parser.parse_args();build(args.table,args.results_dir,args.output_dir)
