"""统一入口：设计、协议与有实际证据的共同活动运行。"""
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
ACTIVITIES=[('snack_service','共同准备点心'),('drink_storage','共同整理饮品'),('drawer_access','共同清理取用区')]


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()


def main():
    cards=[];facts=[]
    for key,label in ACTIVITIES:
        run=ROOT/'results/continuous_v2'/f'joint_activity_{key}_schema_20261007'
        diagnostic=ROOT/'results/continuous_v2'/f'joint_activity_{key}_dev_20261007'
        if (diagnostic/'diagnostic_video_verification.json').exists():
            v=read(diagnostic/'diagnostic_video_verification.json');assert v['status']=='verified'
            cards.append(f'<section><details><summary>{label}：首批接口诊断（主动中断，非完整活动）</summary><p>模型输出被参数／schema校验拒绝，保留现场，不能计完整实验或动态情景覆盖。实际录制到{v["timeline"]["benchmark_end_s"]:.2f}秒。</p><video controls playsinline preload="none" src="{link(diagnostic/"episode/demo.mp4")}"></video><p><a href="{link(diagnostic/"diagnostic_reason.json")}">中断原因与实际数量</a></p></details></section>')
        if not (run/'summary.json').exists():
            failure=read(run/'failure.json') if (run/'failure.json').exists() else None
            status='执行失败，完整错误证据保留' if failure else '尚无完成运行的证据'
            cards.append(f'<section><h2>{label}</h2><p>{status}，不能计动态情景覆盖。</p></section>')
            facts.append({'activity':key,'complete':False,'failure':failure});continue
        assert read(run/'video_verification.json')['status']=='verified'
        if not (run/'interaction_verification.json').exists():
            cards.append(f'<section><h2>{label}</h2><p>运行产物已保存，独立交互核查尚未完成。</p></section>')
            facts.append({'activity':key,'complete':False,'pending_audit':True});continue
        audit=read(run/'interaction_verification.json');assert audit['status']=='verified'
        language=read(run/'language_observation_verification.json') if (run/'language_observation_verification.json').exists() else None
        language_note=(f'独立编码检查发现{language["truncated_calls"]}个调用超过实际200token上限，近期对话或状态会被截断。本批单列输入诊断，不能作为HRC能力结论。' if language and language['status']!='verified' else '')
        m=read(run/'summary.json')['episodes'][0];ep=run/'episode';human=rows(ep/'human_policy_io.jsonl')
        events=[{'time_s':d['time_s'],'private_intention':d['choice'].get('intention'),
                 'public_expression':d['choice'].get('message'),'action':d['choice']['action'],
                 'object':d['choice'].get('object_id'),'destination':d['choice'].get('destination')}
                for d in human if d['choice']['action']!='wait' or d['choice'].get('message')]
        table=''.join(f'<tr><td>{e["time_s"]}</td><td>{escape(e["private_intention"] or "")}</td>'
            f'<td>{escape(e["public_expression"] or "")}</td><td>{escape(e["action"])} {escape(e["object"] or "")} → {escape(e["destination"] or "")}</td></tr>' for e in events)
        cards.append(f'<section><h2>{label}</h2><p>80秒开发运行，人Qwen3-14B在线决策，无旧抓放LoRA；真实π0.5读取双方共享活动说明、实时相机和已公开话语。</p>'
            f'<video controls playsinline preload="metadata" src="{link(ep/"demo.mp4")}" poster="{link(ep/"preview.png")}"></video>'
            f'<p>{language_note}</p><p>人实际推理{audit["human_neural_calls"]}次；机器人{audit["robot_action_blocks"]}个动作块，其中{audit["robot_calls_with_actual_human_speech"]}次调用参数包含人公开话语（实际编码可见性另查）。'
            f'人动作拒绝{audit["human_executor_rejection_count"]}次；连续手运动峰速{audit["human_peak_sampled_kinematic_speed_m_s"]:.3f}m/s。机器人原生目标期末{m["robot_native_goal_terminal"]}。完整共同活动结果仍需结合依赖与实际行为判断。</p>'
            f'<p><a href="{link(run/"index.html")}">视频与实时意图／交流同步</a> · <a href="{link(run/"summary.json")}">完整结果</a> · <a href="{link(run/"interaction_verification.json")}">独立渠道及执行核查</a> · <a href="{link(ep/"model_calls.jsonl")}">机器人实际输入与动作</a></p>'
            '<div class="scroll"><table><tr><th>模拟秒</th><th>人的私有意图（研究记录）</th><th>实际公开表达</th><th>当前动作</th></tr>'+table+'</table></div></section>')
        facts.append({'activity':key,'complete':True,'metrics':m,'language_status':language['status'] if language else 'missing',
                      'interaction_audit':{k:v for k,v in audit.items() if k!='behavior_review'}})
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>动态共同活动：设计与实际进展</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#edf3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{margin:22px 0;background:white;padding:24px;border-radius:14px}}h1,h2,a{{overflow-wrap:anywhere}}video{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}.scroll{{overflow-x:auto}}table{{min-width:850px;width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}@media(max-width:600px){{main{{padding:12px}}section,header{{padding:18px 14px}}}}</style><main><header><h1>动态共同活动：设计与实际进展</h1><p>研究重心回到人的意图、参与方式和双方如何调整共同活动。人执行简化，机器人保留真实模型控制。</p></header><section><h2>为什么改变路线</h2><p>上一轮双方主要各自整理，直接VLA没有收到人的话语，人又受抓放限制；失败不能归因为动态HRC。新设计用人准备—机器人贡献—人接收等实际依赖建立共同活动，公开交流进入VLA真实输入，机器人运动进入人下次决策。</p><p>人的执行使用连续运动学和持物约束，不声称高保真人体物理；机器人仍以原生OSC动作和接触执行，不使用吸附或位姿改写。人只生成一个当前动作，后台不调度任务队列。工作流描述关系，不选择下一策略。</p><p><a href="DESIGN.md">完整Benchmark设计和参考依据</a> · <a href="DEVELOPMENT_PROTOCOL.md">本批固定开发设置</a> · <a href="README.md">实际进展与未完成项</a> · <a href="../interaction_learning_20261007/index.html">前一轮失败视频</a></p></section>{''.join(cards)}<section><h2>证据边界</h2><p>三条是开发案例，不是正式统计矩阵或多模型排名。配置支持、意图文字变化和外部通知不能算动态覆盖。人是否响应、是否修改约定和活动是否真正重组，需要结合原始输入、公开话语、物品变化及双方后续行动判断。</p><p>六类动态情景、多人物和初始化、第二模型／明确不同系统、未见组合、过程指标和数据集导出仍需推进；不以这批原生单物体成绩宣布Goal完成。</p></section></main></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'facts.json').write_text(json.dumps({'goal_complete':False,'development_runs':facts},ensure_ascii=False,indent=2))
    print(json.dumps([{k:v for k,v in f.items() if k!='interaction_audit' and k!='metrics'} for f in facts],ensure_ascii=False))


if __name__=='__main__':main()
