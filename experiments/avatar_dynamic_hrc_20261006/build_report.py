"""完整人物与离返协作阶段报告；原始结果、合格性与运动检查分别呈现。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def href(path):return '../../'+path.relative_to(ROOT).as_posix()
def video(path):return f'<video controls preload="metadata" poster="{href(path/"preview.png")}" src="{href(path/"demo.mp4")}"></video>'


def main():
    sources=[];panels=[];table=[];evidence={}
    runs=[('native_vico_avatar_presence','完整人物的机器人操作参照'),
          ('native_vico_qwen_collaboration','完整人物与动态接收盘'),
          ('native_avatar_clearance_return','退离、返回与等待条件')]
    for name,label in runs:
        root=RESULTS/name
        for filename in ['summary.json','video_verification.json','model_execution_verification.json','avatar_verification.json']:
            assert (root/filename).exists()
            sources.append(root/filename)
        assert read(root/'video_verification.json')['status']=='verified'
        summary=read(root/'summary.json');verification=read(root/'model_execution_verification.json')
        avatar=read(root/'avatar_verification.json')
        valid={Path(r['episode']).resolve():r['motion_eligible'] for r in verification['episodes']}
        avatar_valid={Path(r['episode']).resolve():r['qualification_passed'] for r in avatar['episodes']}
        good=sum(bool(m['task_success']) for m in summary['episodes'])
        table.append(f'<tr><td>{label}</td><td>{good}/{len(summary["episodes"])}</td><td>{verification["motion_eligible_episode_count"]}/{len(summary["episodes"])}</td><td>{avatar["qualified_count"]}/{len(summary["episodes"])}</td></tr>')
        evidence[name]={'summary':summary,'execution':verification,'avatar':avatar}
        sources.append(root/'provenance.json')
        for metric in summary['episodes']:
            directory=root/f'task_{metric["task_id"]:02d}'/f'init_{metric["init_state_id"]:03d}'
            decision_path=directory/'human_policy_io.jsonl';details=''
            if decision_path.exists():
                decisions=rows(decision_path);intents=Counter(r['parsed_decision']['intent'] for r in decisions)
                details=f'<p>真实Qwen决定：{escape("、".join(f"{k} {v}次" for k,v in intents.items()))}；机器人的工作{"完成" if metric["robot_goal_success"] else "未完成"}，人的工作{"完成" if metric["human_goal_success"] else "未完成"}。</p>'
                if metric.get('task_contract'):
                    score=metric['task_contract']
                    details+=f'<p>身体清离：{"已发生" if score["clearance_observed"] else "未发生"}；返回原工作区：{"已发生" if score["return_observed"] else "未完成"}；提前放置{score["premature_placements"]}次。</p>'
                    if score['family']=='clearance_return':
                        details+='<p>本次没有提前放置，但机械臂也没有拿起碗；不能把没有提前放置直接解释为已经理解并正确等待。</p>'
                sources.append(decision_path)
            panels.append(f'''<article><h3>{label} · 场景{metric['task_id']+1}</h3><p>模拟{metric['completion_time_s']:.1f}秒，真实模型调用{metric['model_calls']}次。结果：{"完成" if metric['task_success'] else "未完成"}；物理运动资格{"通过" if valid[directory.resolve()] else "未通过"}；人物显示资格{"通过" if avatar_valid[directory.resolve()] else "未通过"}。</p>{video(directory)}{details}<p>显示手指与物理接触点最大偏差{metric['avatar_maximum_alignment_error_m']*1000:.1f}mm。<a href="{href(directory/'metrics.json')}">原始结果</a> · <a href="{href(root/'model_execution_verification.json')}">独立执行核查</a></p></article>''')
    motion_root=RESULTS/'native_avatar_body_clearance'
    motion=read(motion_root/'summary.json')['episodes'][0]
    assert read(motion_root/'video_verification.json')['status']=='verified'
    assert read(motion_root/'avatar_verification.json')['qualified_count']==1
    sources.extend(motion_root/p for p in ['summary.json','video_verification.json','avatar_verification.json'])
    motion_panel=f'''<article><h3>低层步行执行器检查 · 不计入人类策略成绩</h3><p>脚本给出退离和返回命令，人物从工作位连续后退再返回；完整8秒真实Sim。站位最大Y={motion['maximum_body_y']:.3f}m，结束Y={motion['final_body_position'][1]:.3f}m，接触点对齐偏差{motion['avatar_maximum_alignment_error_m']*1000:.1f}mm。这里验证运动执行器，机器人保持末端，没有生成式人类决策。</p>{video(motion_root/'body_clearance_and_return')}</article>'''
    result={'status':'execution_evidence','research_goal_achieved':False,'runs':evidence,
            'source_sha256':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sources},
            'interpretation':'真实模型运行与人物显示/运动执行器验证，不推断真人行为、完整人体动力学或成熟Benchmark完成。'}
    (HERE/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完整人物与动态协作任务 · 实际进展</title><style>*{{box-sizing:border-box}}body{{background:#f1f5f4;color:#193540;font:17px/1.85 system-ui;margin:0;overflow-wrap:anywhere}}main{{max-width:1100px;margin:auto;padding:28px 20px}}header{{background:#173f48;color:white;padding:30px;border-radius:16px}}section,article{{background:white;padding:26px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(26px,4vw,38px);line-height:1.4}}h2{{font-size:25px}}h3{{font-size:21px}}video{{width:100%;max-height:640px;background:#142430}}a{{color:#137a7b}}.notice{{background:#fff3e2;border-left:5px solid #b47731;padding:18px}}.table-wrap{{overflow:auto}}table{{width:100%;min-width:700px;border-collapse:collapse}}td,th{{padding:12px;border-bottom:1px solid #d1dfdd;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:20px 16px}}}}</style><main>
<header><h1>完整人物、真实动作连接与离返协作</h1><p>本轮替换胶囊人体，复用已有VICO贴图、65骨骼与动作资产。在同一MuJoCo物理场景中，真实π0.5驱动机械臂，Qwen决定人的意图，人物动作连接实际受力接触点。这里分别呈现显示改进、运动执行器与真实策略结果。</p></header>
{motion_panel}
<section><h2>目的与完成内容</h2><p>此前已经出现真实模型共同完成，但人体只有胶囊和指尖。现在人物有完整外观和骨骼，站姿、步行来自本地动作资产，伸手用有限姿态与角速度的IK跟踪接触点。
MuJoCo实际蒙皮顶点与原资产计算一致，骨骼长度保持，贴图和动作在真实视频中检查。首次画面发现贴图翻转和过度躯干弯折，旧片段保留诊断；校正后的人物操作参照3/3。</p>
<p>行走用步行动作连续插值，低层可执行退让、退离、返回；何时发命令由生成式伙伴决定。身体是运动学显示，物体操作仍由力驱动指尖代理负责，不能称为完整人体或手掌动力学。</p></section>
<section><h2>两个实际协作关系</h2><p><strong>动态接收盘：</strong>人想把盘子移近自己，机器人要把指定碗放上去；盘子的位置和接触随人的行动变化。</p>
<p><strong>退离、返回与等待：</strong>人先退出共享空间、再回来准备盘子。机器人可以拿碗，但放置需等人返回且盘子准备好。要求通过公开语言给模型，评分只记录真实动作时序；早放不能在之后自动获得贡献，必须重新操作。</p>
<p>没有固定第N个tick让人离席，也没有由评分器决定双方策略。NativeQwen选择push、observe、away、return等意图，π0.5输出原生7维动作。三个摆放变化仍属于同一取放技能；新任务扩展了协作时序，尚非全面多样化任务集。</p></section>
<section><h2>原始结果与核查</h2><div class="table-wrap"><table><thead><tr><th>条件</th><th>任务完成</th><th>物理运动资格</th><th>人物显示资格</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<div class="notice">外观和动作连接通过不等于人的策略可靠。本轮三项动态接收盘中Qwen持续observe，机器人都完成、人都未完成。
离返任务中Qwen真实发出away和return，但在半路observe停下，未完成返回/移盘；机器人没有拿碗，也没有提前放置。不能把代理停滞归为机器人普遍没有协作能力，也不能把零提前放置当作等待理解已经验证。</div>
<p>只有合作型persona、一个VLA和少量场景。不同批次模型采样未严格配对，人物外观与接口也有变化，不能据此声称因果提升。上一阶段的合格共同完成继续保留：<a href="{href(ROOT/'experiments/native_dynamic_hrc_20261006/index.html')}">真实原生模型与动态接收盘报告</a>。</p></section>
{''.join(panels)}
<section><h2>仍需完成</h2><p>生成式人的执行可靠性、真实手部抓持、身体碰撞/动力学、更多意图和任务、多人格、多先进算法与统计协议仍缺乏验证。本轮不是成熟Benchmark完成。
下一阶段应把人的目标与实际执行进展接起来，扩展真实协调关系和模型覆盖，继续保留失败视频与资格检查，避免只扩大简化代理的任务计数或反复微调同一小问题。</p></section></main></html>'''
    (HERE/'index.html').write_text(html);print(HERE/'index.html')


if __name__=='__main__':main()
