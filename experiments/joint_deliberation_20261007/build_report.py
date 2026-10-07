"""报告联合意图动作推理的自主操作与真实学习模型共同活动。"""
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RUNS={'qualification':('自主操作：机器人实际泊车',ROOT/'results/continuous_v2/joint_deliberation_qualification_20261007'),
    'food_into_bowl':('奶酪入碗与自主整理',ROOT/'results/continuous_v2/joint_deliberation_20261007/food_into_bowl'),
    'bowl_on_stove':('碗放炉面与自主用餐',ROOT/'results/continuous_v2/joint_deliberation_20261007/bowl_on_stove')}
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()
NAMES={'akita_black_bowl_1':'黑碗','wine_bottle_1':'酒瓶','plate_1':'餐盘','cream_cheese_1':'奶酪包'}


def main():
    panels=[];table=[];data={};facts=[]
    for key,(label,run) in RUNS.items():
        solo=key=='qualification';ep=run/'human_activity' if solo else next(run.glob('task_*/init_000'))
        for name in ['video_verification','personal_verification','human_feedback_verification','relative_geometry_verification']:
            assert read(run/(name+'.json'))['status']=='verified'
        if solo:assert read(run/'qualification_verification.json')['status']=='verified'
        else:assert read(run/'model_execution_verification.json')['status']=='verified'
        assert not read(run/'provenance.json')['source_files_changed_during_run']
        m=read(run/'summary.json')['episodes'][0];human=rows(ep/'human_policy_io.jsonl');plans=rows(ep/'human_planner_io.jsonl') if (ep/'human_planner_io.jsonl').exists() else []
        assert all(json.loads(h['public_input'].split('\n',1)[1])['human_input_contract']=='joint_intention_action_v1' for h in human)
        continuous=read(run/'continual_activity_verification.json')['episodes'][0]
        contact=read(run/'hand_robot_contact_verification.json')['episodes'][0]
        hand=read(run/'hand_verification.json')['episodes'];motion=all(h['motion_qualified'] for h in hand) and read(run/'avatar_verification.json')['status']=='verified'
        if not solo:motion=motion and read(run/'model_execution_verification.json')['motion_eligible_episode_count']==1
        vla=m.get('actual_vla_model_calls',0);robot_success=None if solo else m['robot_goal_success']
        commands=Counter(h['parsed_decision']['intent'] for h in human)
        objects=Counter(h['parsed_decision']['object_id'] for h in human if h['parsed_decision']['intent'] in {'grasp','place','push'})
        scope=read(run/'human_goal_action_scope.json')['episodes'][0]['decision_counts']
        goalrows=''.join(f'<tr><td>{escape(t["object_id"])}</td><td>{escape(t["destination"])}</td><td>{t["first_stable_relation_s"] if t["first_stable_relation_s"] is not None else "未满足"}</td><td>{"满足" if t["terminal_relation_satisfied"] else "未满足"}</td></tr>' for t in m['personal_evidence']['target_intervals'])
        table.append(f'<tr><td>{label}</td><td>{vla}</td><td>{len(human)}</td><td>{continuous["semantic_target_set_changes"]}</td><td>{"不适用" if solo else robot_success}</td><td>{m["human_goal_success"]}</td><td>{"不适用" if solo else str(continuous["joint_released_goal_time_s"])+"s"}</td><td>{"通过" if motion else "诊断"}</td></tr>')
        coverage=''
        if not solo:
            receiver=m['robot_goal_receiver'];inventory=read(run/'scene_integrity_verification.json')['episodes'][0]['objects']
            record=next((r for r in inventory if r['object_id']==receiver),None)
            selected=sum(h['parsed_decision']['object_id']==receiver and h['parsed_decision']['intent'] in {'grasp','place','push'} for h in human)
            if record:
                coverage=f'接收物{receiver}最大位置变化{record["maximum_displacement_m"]*1000:.2f}mm，人选择操作它{selected}次。'
                if not selected:coverage+='没有实现人自主操作接收物的预期条件，不能把任务模板当作动态压力覆盖。'
        buttons='<button data-video="'+key+'" data-time="'+('4' if solo else '0')+'">活动开始</button>'
        panels.append(f'''<section><h2>{label}</h2><p>{'前4秒实际控制泊车，之后60秒人自主选择活动；机器人模型调用0，不计作HRC成绩。' if solo else '真实π0.5与生成式人在同一世界持续60秒；没有定时目标更新或人动作清单。'}</p><video id="{key}" controls playsinline preload="metadata" poster="{link(ep/'preview.png')}" src="{link(ep/'demo.mp4')}"></video>{buttons}<pre id="state-{key}"></pre><p class="notice">{'运动／显示资格通过，不等于人策略或任务成功。' if motion else '运动阈值未通过，仅诊断保留，不纳入合格Benchmark成绩。'}人期末目标{'满足' if m['human_goal_success'] else '未满足'}，{'可评分' if m['human_goal_evaluable'] else '不可评分，空目标不算成功'}。手／机械臂几何接触{contact['hand_robot_contact_record_time_s']:.2f}秒。</p><p>模型选择：{escape('，'.join(f'{k} {v}次' for k,v in commands.items()))}。{escape(coverage)}</p><div class="scroll"><table><tr><th>个人物品</th><th>当前关系</th><th>首次释放稳定满足（秒）</th><th>期末</th></tr>{goalrows}</table></div><p><a href="{link(run/'summary.json')}">实际结果</a> · <a href="{link(run/'personal_verification.json')}">当次目标与几何重建</a> · <a href="{link(ep/'human_policy_io.jsonl')}">原始动作与收到的输入</a> · <a href="{link(run/'video_verification.json')}">视频核验</a></p></section>''')
        description=f'选择操作当前目标对象{scope.get("current_personal_target_object",0)}次，目标接收物{scope.get("current_personal_goal_receiver",0)}次，其他物品{scope.get("other_visible_object",0)}次，非物品操作{scope.get("no_object_manipulation_selected",0)}次。其他物品操作可能是帮助或准备，不自动判错。'
        panels[-1]=panels[-1].replace('<div class="scroll"><table><tr><th>个人物品</th>',f'<p>{description}</p><div class="scroll"><table><tr><th>个人物品</th>')
        panels[-1]=panels[-1].replace('<video ',f'<p>每次完整推理同时选择意图与动作，共{len(human)}次真实模型调用。解析失败{sum(h["parse_error"] is not None for h in human)}次。目标集合变化{continuous["semantic_target_set_changes"]}次；机器人物理任务累计成立{continuous["robot_physical_goal_time_s"] if not solo else "不适用"}秒。</p><video ',1)
        selected='，'.join(f'{NAMES.get(obj,obj)} {count}次' for obj,count in objects.items()) or '没有选择物品操作'
        panels[-1]=panels[-1].replace('<video ',f'<p>实际选择的操作对象：{escape(selected)}。这些是模型选择次数，实际抓持、搬运与稳定放置需结合视频及下面的关系证据判断。</p><video ',1)
        data[key]={'frames':read(ep/'video_timeline.json')['frames'],'decisions':[{
            'time_s':h['time_s'],'decision':h['parsed_decision'],
            'current_targets':h['personal_goal_state']['personal_targets'],
            'previous_targets':json.loads(h['public_input'].split('\n',1)[1])['your_previous_personal_targets'],
            'objects':json.loads(h['public_input'].split('\n',1)[1])['objects_xyz'],
            'received_execution':json.loads(h['public_input'].split('\n',1)[1])['your_measured_execution']} for h in human]}
        facts.append({'scene':key,'motion_qualified':motion,'actual_vla_calls':vla,'human_inferences':len(plans)+len(human),
            'robot_goal_success':robot_success,'human_goal_success':m['human_goal_success'],
            'human_goal_evaluable':m['human_goal_evaluable'],'human_goal_changes':continuous['semantic_target_set_changes'],
            'joint_goal_time_s':None if solo else continuous['joint_released_goal_time_s'],'human_commands':dict(commands)})
        facts[-1]['human_goal_action_scope']=scope
        facts[-1].update(selected_object_counts=dict(objects),robot_goal_time_s=None if solo else continuous['robot_physical_goal_time_s'],
            parse_errors=sum(h['parse_error'] is not None for h in human),target_intervals=m['personal_evidence']['target_intervals'])
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>联合推理与真实共同用餐</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{margin:22px 0;background:white;padding:24px;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px)}}h2{{font-size:24px}}video{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef5f2;padding:16px}}.notice{{background:#fff1d8;padding:16px;border-radius:8px}}.scroll{{overflow-x:auto}}table{{min-width:780px;width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}button{{font:inherit;padding:7px 12px;cursor:pointer;margin:8px}}@media(max-width:600px){{main{{padding:12px}}section,header{{padding:18px 14px}}}}</style><main><header><h1>联合推理与真实共同用餐</h1><p>一个自主操作场景、两种真实学习机器人活动。直接观察一次完整推理如何选择意图与动作。</p></header><section><h2>为什么需要这轮</h2><p>上一轮人的长期意图与当前动作由两次独立推理生成，出现持续抓取机器人任务物品、反复操作第一件物品、第二件目标未推进等行为。本轮将意图与下一动作放在同一次完整神经推理中，允许模型在活动中自主改变安排。</p><p>人有自主共同用餐的个人背景；Qwen3-14B同时生成私人目标、计划说明与一个当前动作。计划不会排队执行，没有自动按目标成绩选动作或定时修改目标。参考<a href="https://github.com/dannymcy/coopera_code/blob/main/HUMAN.md">COOPERA人模拟</a>的背景、环境与意图历史建模思想，实际动力学使用本项目真实双指受力代理。</p></section><section><h2>设置与判断方式</h2><p>init0／seed0、20Hz、60秒，一次世界／人初始化。人每2秒一次联合意图动作推理；新消息可触发额外推理。thinking模式上限3072token，只有结束思考后的最终JSON参与动作执行。共同活动为真实π0.5原生7维控制。人读理想几何、身体为骨骼显示、手为双指受力代理。完整人体、五指和心理效度未验证。</p><p>视频为运行时三机位直接录制，按模拟时间播放；推理墙钟较慢。下方分别显示当次输入的上次目标、当次选择的目标、物体测量与动作。输入旧意图与输出新意图分开，原始推理可通过链接检查。绿色输入／视频核验不代表行为成功，也不能替代动态条件实际发生。</p><p><a href="PLAN.md">运行协议</a> · <a href="README.md">实际行为与未完成项</a> · <a href="../spatial_coordination_20261007/index.html">前一批原始结果</a></p></section><section><h2>实际结果</h2><div class="scroll"><table><tr><th>场景</th><th>VLA调用</th><th>人单次联合推理</th><th>目标变化</th><th>机器人期末</th><th>人期末</th><th>共同目标时间</th><th>运动资格</th></tr>{''.join(table)}</table></div></section>{''.join(panels)}<section><h2>结论边界</h2><p>是否实现了可靠自主活动、目标变化和双方协调，以实际目标关系与动作判断；输入更清楚不能直接称为能力提升。前后并非严格配对，不能作单因子因果或模型排名。成熟Dynamic Human Policy HRC Benchmark与cobalance效度仍未完成。</p></section></main><script>const runs={payload};for(const [key,r]of Object.entries(runs)){{const v=document.getElementById(key),s=document.getElementById('state-'+key);function update(){{let f=r.frames[0];for(const a of r.frames)if(a.video_time_s<=v.currentTime)f=a;if(f.benchmark_time_s===null){{s.textContent='实际控制泊车；自主人活动尚未开始。';return;}}let d=r.decisions[0];for(const a of r.decisions)if(a.time_s<=f.benchmark_time_s)d=a;s.textContent=`模拟 ${{f.benchmark_time_s.toFixed(2)}}秒 · 最新动作推理 ${{d.time_s.toFixed(2)}}秒\n当次选择的个人目标：${{JSON.stringify(d.current_targets)}}\n输入的上次目标：${{JSON.stringify(d.previous_targets)}}\n当次物体测量：${{JSON.stringify(d.objects)}}\n选择：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n理由：${{d.decision.reason}}\n该次输入的实际握持：${{d.received_execution.object_measured_in_hand||'无'}}；阶段：${{d.received_execution.motor_phase}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}document.querySelectorAll('button').forEach(b=>b.onclick=()=>document.getElementById(b.dataset.video).currentTime=Number(b.dataset.time));</script></html>'''
    html=html.replace('<h2>结论边界</h2>', '<h2>结论边界</h2><p>本轮同时改变了推理结构、推理模式与个人活动背景，不能作单因子因果改善归因。模型是否可靠推进第二物品、产生目标变化和操作接收物，以各场实际记录为准；没有发生的动态条件不计覆盖。失败与运动不合格轨迹真实保留，不作为专家示范。</p>')
    (HERE/'index.html').write_text(html);(HERE/'facts.json').write_text(json.dumps({'research_goal_achieved':False,'episodes':facts},ensure_ascii=False,indent=2));print(json.dumps(facts,ensure_ascii=False))

if __name__=='__main__':main()
