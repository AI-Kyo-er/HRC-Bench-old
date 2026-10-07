"""从正式运行证据生成真实Sim视频报告；缺少核验时不发布。"""
import json
from collections import Counter
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DATA=ROOT/'datasets/interaction_contact_20261007'
TRAIN=ROOT/'results/interaction_contact_lora_train_20261007'
RUNS=[('qualification','独立操作资格：碗与酒瓶','interactive_human_qualification_20261007'),
      ('food','共同活动：奶酪入碗','interactive_hrc_food_20261007'),
      ('stove','共同活动：碗放炉面','interactive_hrc_stove_20261007')]


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()


def main():
    training=read(TRAIN/'summary.json')
    assert training['status']=='trained' and not training['source_files_changed_during_run']
    assert training['adapter_parameter_delta_norm']>0 and training['steps']==200
    panels=[];teacher_panels=[];facts=[];payload={};teacher_total=0
    for sub in ['moving','plate']:
        base=DATA/sub
        video=read(base/'video_verification.json');audit=read(base/'training_data_verification.json')
        assert video['status']=='verified' and audit['status']=='verified'
        teacher_total+=video['verified_episode_count']
        cards=[]
        for entry in read(base/'summary.json')['episodes']:
            ep=base/'episodes'/entry['episode_id'];metric=read(ep/'metrics.json')
            names=[t['object_id'] for t in entry['targets']]
            stable=entry['terminal_released_stable_targets']
            cards.append(f'<details><summary>{escape(entry["episode_id"])} · 期末目标 {len(stable)}/{len(names)}</summary>'
                f'<p>人动作来自数据教师，实际人模型调用0；机器人模型调用{entry.get("robot_neural_calls",0)}。'
                '是否进入监督数据还要满足运动与完整目标核查。</p>'
                f'<video controls playsinline preload="none" src="{link(ep/"demo.mp4")}"></video>'
                f'<p><a href="{link(ep/"metrics.json")}">完整结果</a></p></details>')
        teacher_panels.append('<section><h2>数据生成视频：'+('真实π0.5活动' if sub=='moving' else '餐盘与酒瓶，机器人泊车')+'</h2><p>所有新增轨迹完整保存，包含失败和未入选数据。这些视频不计作学习伙伴成绩。</p>'+''.join(cards)+'</section>')
    for key,label,name in RUNS:
        run=ROOT/'results/continuous_v2'/name;solo=key=='qualification'
        for stem in ['video_verification','personal_verification','human_feedback_verification',
                     'human_command_delivery_verification',
                     'qualification_verification' if solo else 'model_execution_verification']:
            assert read(run/(stem+'.json'))['status']=='verified'
        p=read(run/'provenance.json')
        assert not p['source_files_changed_during_run'] and not p['human_adapter_files_changed_during_run']
        ep=run/'human_activity' if solo else next(run.glob('task_*/init_*'))
        m=read(run/'summary.json')['episodes'][0];human=rows(ep/'human_policy_io.jsonl')
        counts=dict(Counter(d['parsed_decision']['intent'] for d in human))
        contact=read(run/'hand_robot_contact_verification.json')['episodes'][0]
        activity=read(run/'continual_activity_verification.json')['episodes'][0]
        motion=all(e['motion_qualified'] for e in read(run/'hand_verification.json')['episodes'])
        if not solo:motion=motion and read(run/'model_execution_verification.json')['motion_eligible_episode_count']==1
        goals=m['personal_evidence']['target_intervals']
        goalrows=''.join(f'<tr><td>{escape(t["object_id"])}</td><td>{t["first_stable_relation_s"] if t["first_stable_relation_s"] is not None else "未满足"}</td><td>{"成立" if t["terminal_relation_satisfied"] else "未成立"}</td></tr>' for t in goals)
        setting='前4秒真实控制泊车，再运行60秒；机器人模型调用0，此项不计HRC成绩。' if solo else '真实π0.5与学习伙伴同一世界运行60秒；机器人仅接收原任务语言、实时图像与机械臂状态。'
        result=f'人期末整体目标{"成立" if m["human_goal_success"] else "未成立"}；运动资格{"通过" if motion else "未通过，保留诊断"}。'
        if not solo:result+=f'机器人期末目标{m["robot_goal_success"]}，共同释放稳定目标满足累计{activity["joint_released_goal_time_s"]:.2f}秒。'
        panels.append(f'<section><h2>{label}</h2><p>未见init4／seed4，实际Qwen3-14B＋最终200步LoRA，{len(human)}次人模型推理。{setting}</p>'
            f'<video id="{key}" controls playsinline preload="metadata" src="{link(ep/"demo.mp4")}" poster="{link(ep/"preview.png")}"></video><pre id="state-{key}"></pre>'
            f'<p>{result}</p><p>手与机械臂几何接触累计{contact["hand_robot_contact_record_time_s"]:.2f}秒；'
            f'{contact["decision_count_with_direct_hand_contact_feedback"]}/{len(human)}次决策输入包含直接接触测量。动作计数：{escape(str(counts))}。</p>'
            '<div class="scroll"><table><tr><th>人选择的物品</th><th>首次释放稳定（秒）</th><th>期末关系</th></tr>'+goalrows+'</table></div>'
            f'<p><a href="{link(ep/"human_policy_io.jsonl")}">完整模型输入与原始推理</a> · <a href="{link(run/"summary.json")}">全部结果</a> · '
            f'<a href="{link(run/"provenance.json")}">模型和设置</a> · <a href="{link(run/"video_verification.json")}">逐帧视频核验</a></p></section>')
        payload[key]={'frames':read(ep/'video_timeline.json')['frames'],
            'decisions':[{'time_s':d['time_s'],'decision':d['parsed_decision'],
                          'goals':d['personal_goal_state']['personal_targets'],
                          'hand_target':d.get('hand_target_xyz'),
                          'contact':json.loads(d['public_input'].split('\n',1)[1])['hand_contact_summary']} for d in human]}
        facts.append({'scene':key,'human_goal_success':m['human_goal_success'],'motion_qualified':motion,
            'human_calls':len(human),'actions':counts,'contact_time_s':contact['hand_robot_contact_record_time_s'],
            'direct_contact_feedback_calls':contact['decision_count_with_direct_hand_contact_feedback'],
            'robot_goal_success':None if solo else m['robot_goal_success'],
            'joint_goal_time_s':None if solo else activity['joint_released_goal_time_s']})
    data_json=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')
    learning=f'200步真实训练，{training["trainable_parameters"]:,}个LoRA参数更新，变化范数{training["adapter_parameter_delta_norm"]:.4f}；验证回答损失{training["initial_dev_loss"]:.4f}→{training["final_dev_loss"]:.6f}。'
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>接触历史与机器人活动的学习实测</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#edf3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{margin:22px 0;background:white;padding:24px;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px)}}h1,h2,a,summary{{overflow-wrap:anywhere}}video,img{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef5f2;padding:16px}}details{{margin:18px 0}}.scroll{{overflow-x:auto}}table{{min-width:500px;width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}@media(max-width:600px){{main{{padding:12px}}section,header{{padding:18px 14px}}}}</style><main><header><h1>接触历史与机器人活动的学习实测</h1><p>12段数据生成视频与3段实际模型闭环视频。每段视频由运行中的MuJoCo相机直接记录，保留完整过程及失败。</p></header><section><h2>实验要回答什么</h2><p>此前模型独立完成碗与酒瓶整理，但与机器人共同活动时受阻；精简输入遗漏了直接手／机械臂接触。本轮让伙伴看到当前真实接触与过去两次测量、选择真实手部空间动作，并通过机器人活动数据学习，再检查未见初始化中的操作和共同完成。三个因素同时变化，结果不能单独归因于其中一项。</p><p><a href="README.md">完整报告</a> · <a href="PLAN.md">实验设置</a> · <a href="../human_action_learning_20261007/index.html">上一轮实际视频</a></p></section><section><h2>人和机器人如何行动</h2><p>人由实际Qwen3-14B＋LoRA每2秒联合生成自己的当前目标和下一动作。读取理想几何、真实握持与接触测量；可抓、放、观察、退开或选择move_hand的空间位置。低层双指代理以受力控制执行，不吸附物体、不写物体位置，也不按成绩自动选下一目标。身体主要是骨骼显示，尚不是完整人体或五指控制。</p><p>机器人由真实π0.5每10个控制步重新推理，读取两路实时图像、机械臂状态及原任务语言，输出7维OSC动作；20Hz推进物理。task_only接口不把人的私人目标或协商文本附加到机器人指令，因此不能将这批结果视为已验证语言协商能力。</p><p>人的目标由模型自选；释放稳定关系、操作接触见证、机器人目标持续成立时间、共同成立时间及运动异常分别报告。目标文字变化与视频核验通过均不等于cobalance能力成立。</p></section><section><h2>数据与真实参数学习</h2><p>新增8条真实机器人活动轨迹、4条餐盘／酒瓶轨迹，每条80秒；只有炉面场景4条完成两物品且运动合格，其余8条保留诊断。与原16条合格静止机器人范例合并，监督640对（训练440，验证200）；init3整episode用于验证，init4闭环测试。同stem输入／标签匹配。成功范例覆盖仍窄，餐盘泛化和入碗场景阻挡尚未得到合格示范覆盖。</p><p>使用已有本地中国源权重，基础模型冻结，BF16单卡训练，rank8、q_proj/v_proj、学习率0.0001、累积4、最长4096token，200固定步、seed41。{learning}这些数值验证参数确实更新，不证明闭环能力。</p><img src="{link(TRAIN/"loss_curve.svg")}" alt="真实训练和验证回答损失曲线，对数纵轴"><p><a href="{link(TRAIN/"summary.json")}">真实训练记录</a> · <a href="{link(DATA/"combined/training_data_verification.json")}">数据资格</a>。</p></section>{''.join(panels)}{''.join(teacher_panels)}<section><h2>结论与适用边界</h2><p>三场人整体目标均失败，两个共同活动机器人期末目标成立，但共同满足时间均0。独立场景仅碗16.45秒首次释放稳定，随后观察、酒瓶没有推进；food场景30次抓酒瓶且累计57.35秒手／机械臂接触；炉面场景先抓餐盘再重复抓奶酪，同样没有完成抓放。三场均没有选择move_hand，没有自主目标集合变化。30/30次决策保留直接接触测量仍未产生恢复动作，因此接口开放和数据学习尚未形成可靠交互策略。这些配置同时变化，不能宣称改善，也不能将单次失败外推为所有模型能力边界。以上是少量正式闭环系统实测，未构成多任务、多初始化的统计排名。成功和失败都需要结合接触、动作与稳定关系判断；神经伙伴行为不等同于真人行为，理想几何和双指代理限制外推。成熟Dynamic Human Policy HRC Benchmark、完整人体、可靠动态意图与cobalance构念效度仍未完成。</p><p>重要实验必须先核验非空视频、逐帧解码、FPS、帧数及轨迹起止时间覆盖，再发布HTML。视频是主展示，轨迹与模型记录用于审计，不以轨迹动画替代真实场景。</p></section></main><script>const data={data_json};for(const[key,r]of Object.entries(data)){{const v=document.getElementById(key),s=document.getElementById('state-'+key);function update(){{let f=r.frames[0];for(const a of r.frames)if(a.video_time_s<=v.currentTime)f=a;if(f.benchmark_time_s===null){{s.textContent='真实控制泊车，自主活动尚未开始。';return;}}let d=r.decisions[0];for(const a of r.decisions)if(a.time_s<=f.benchmark_time_s)d=a;s.textContent=`模拟 ${{f.benchmark_time_s.toFixed(2)}}秒 · 最新人模型回答 ${{d.time_s.toFixed(2)}}秒\n自选目标：${{JSON.stringify(d.goals)}}\n实际接收动作：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n空间动作位置：${{JSON.stringify(d.hand_target)}}\n当次接触测量：${{JSON.stringify(d.contact)}}\n模型解释：${{d.decision.reason}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'facts.json').write_text(json.dumps({'research_goal_achieved':False,'training':training,
        'new_teacher_videos_verified':teacher_total,'episodes':facts},ensure_ascii=False,indent=2))
    print(json.dumps(facts,ensure_ascii=False))


if __name__=='__main__':main()
