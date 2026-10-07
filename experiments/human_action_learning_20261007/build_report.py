"""真实教师数据、参数学习与闭环人模型结果的独立视频报告。"""
import json
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
DATA=ROOT/'datasets/human_contact_teacher_20261007'
TRAIN=ROOT/'results/human_contact_lora_train_20261007'
RUNS={'step40':('40步阶段检查',ROOT/'results/continuous_v2/learned_human_step40_qualification_20261007'),
    'learned_food':('完成训练：未见奶酪场景初始化',ROOT/'results/continuous_v2/learned_human_qualification_20261007'),
    'learned_drawer':('完成训练：未见餐盘物品组合',ROOT/'results/continuous_v2/learned_human_drawer_qualification_20261007'),
    'learned_hrc':('原生π0.5与学习伙伴共同活动',ROOT/'results/continuous_v2/learned_hrc_food_20261007')}
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()


def main():
    audit=read(DATA/'training_data_verification.json');assert audit['status']=='verified' and read(DATA/'video_verification.json')['status']=='verified'
    episodes=read(DATA/'summary.json')['episodes'];records=rows(TRAIN/'training.jsonl') if (TRAIN/'training.jsonl').exists() else []
    complete=(TRAIN/'summary.json').exists();summary=read(TRAIN/'summary.json') if complete else None
    if complete:assert not summary['source_files_changed_during_run'] and summary['adapter_parameter_delta_norm']>0
    panels=[];facts=[];payload={}
    selected=['food_into_bowl__init000__order0','food_into_bowl__init000__order1','drawer_access__init003__order1']
    for name in selected:
        ep=DATA/'episodes'/name;metric=read(ep/'metrics.json')
        panels.append(f'<section><h2>训练范例：{escape(name)}</h2><p>几何教师用于数据生成，模型调用0；完成两个物品的真实释放稳定整理。该视频不计作人模型或HRC成绩。</p><video controls playsinline preload="metadata" src="{link(ep/"demo.mp4")}" poster="{link(ep/"preview.png")}"></video></section>')
    for key,(label,run) in RUNS.items():
        if not (run/'summary.json').exists():continue
        solo=key!='learned_hrc'
        required=['video_verification','personal_verification','human_feedback_verification','human_command_delivery_verification',
            'qualification_verification' if solo else 'model_execution_verification']
        for name in required:
            if not (run/(name+'.json')).exists():break
            assert read(run/(name+'.json'))['status']=='verified'
        else:
            ep=run/'human_activity' if solo else next(run.glob('task_*/init_*'));m=read(run/'summary.json')['episodes'][0];human=rows(ep/'human_policy_io.jsonl');p=read(run/'provenance.json')
            assert not p['source_files_changed_during_run'] and not p['human_adapter_files_changed_during_run'] and p['human_adapter_sha256']
            hand=read(run/'hand_verification.json');motion=all(r['motion_qualified'] for r in hand['episodes'])
            if not solo:motion=motion and read(run/'model_execution_verification.json')['motion_eligible_episode_count']==1
            initialization=p['init_state_id'] if solo else m['init_state_id']
            setting='前4秒实际机器人泊车，之后60秒活动，机器人模型调用0。' if solo else '学习人策略与真实π0.5同一世界持续60秒；机器人只收到原任务语言。'
            boundary='不是HRC或真人效度成绩。' if solo else f'机器人期末目标{m["robot_goal_success"]}；共同满足时间{read(run/"continual_activity_verification.json")["episodes"][0]["joint_released_goal_time_s"]}秒。'
            targets=m['personal_evidence']['target_intervals'];goalrows=''.join(f'<tr><td>{escape(t["object_id"])}</td><td>{t["first_stable_relation_s"] or "未满足"}</td><td>{"成立" if t["terminal_relation_satisfied"] else "未成立"}</td><td>{t["human_contact_in_target_interval"]}</td></tr>' for t in targets)
            panels.append(f'<section><h2>{label}</h2><p>实际Qwen3-14B＋LoRA权重，{len(human)}次完整神经推理；init{initialization}／seed{p["seed"]}没有用于训练。{setting}</p><video id="{key}" controls playsinline preload="metadata" src="{link(ep/"demo.mp4")}" poster="{link(ep/"preview.png")}"></video><pre id="state-{key}"></pre><p>整体个人目标：{"成立" if m["human_goal_success"] else "未成立"}；运动检查：{"通过" if motion else "诊断保留"}。{boundary}</p><div class="scroll"><table><tr><th>个人物品</th><th>首次释放稳定关系（秒）</th><th>期末</th><th>人接触见证</th></tr>{goalrows}</table></div><p><a href="{link(ep/"human_policy_io.jsonl")}">实际原始神经输出</a> · <a href="{link(run/"human_command_delivery_verification.json")}">真实请求与控制核查</a> · <a href="{link(run/"provenance.json")}">实际加载权重身份</a> · <a href="{link(run/"summary.json")}">完整结果</a></p></section>')
            payload[key]={'frames':read(ep/'video_timeline.json')['frames'],'decisions':[{'time_s':h['time_s'],'decision':h['parsed_decision'],'goals':h['personal_goal_state']['personal_targets']} for h in human]}
            facts.append({'scene':key,'human_goal_success':m['human_goal_success'],'motion_qualified':motion,'human_model_calls':len(human),'init_state_id':initialization,'seed':p['seed'],'adapter':p['human_adapter'],'robot_goal_success':None if solo else m['robot_goal_success'],'joint_goal_time_s':None if solo else read(run/'continual_activity_verification.json')['episodes'][0]['joint_released_goal_time_s']})
    if complete:
        learning=f'训练完成{summary["steps"]}步，更新{summary["trainable_parameters"]:,}个LoRA参数，参数变化范数{summary["adapter_parameter_delta_norm"]:.4f}。验证集回答损失{summary["initial_dev_loss"]:.3f}→{summary["final_dev_loss"]:.3f}；这些数字不代表闭环行为成功。'
    else:learning=f'训练正在推进，已保存{records[-1]["step"] if records else 0}个优化步；模型行为以独立闭环实测为准。'
    points=''
    if records:
        maxloss=max(r['train_loss'] for r in records);points=' '.join(f'{i/max(1,len(records)-1)*700:.1f},{170-r["train_loss"]/maxloss*150:.1f}' for i,r in enumerate(records))
    payload_json=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真实接触范例与神经伙伴学习</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#edf3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{margin:22px 0;background:white;padding:24px;border-radius:14px}}h1{{font-size:clamp(26px,4vw,36px)}}h1,h2,a{{overflow-wrap:anywhere}}video{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef5f2;padding:16px}}.scroll{{overflow-x:auto}}table{{min-width:650px;width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}@media(max-width:600px){{main{{padding:12px}}section,header{{padding:18px 14px}}}}</style><main><header><h1>真实接触范例与神经伙伴学习</h1><p>从已经完成两物品整理的真实执行，训练模型选择动作，再检查未见初始化下的实际行为。</p></header><section><h2>为什么进入学习</h2><p>此前修补旧请求重启后，生成模型仍反复抓已放好的碗、没有推进酒瓶。本轮不再修改提示来等待更好表现：先生成真实可行抓放范例，更新模型参数，再独立运行。</p><p>学习的是高层意图与动作选择，受力控制仍由接触执行器完成；没有训练人体或五指运动网络。正式模型不调用几何教师，也没有按目标成绩自动选择下一任务。人读取理想几何测量，完整人体／心理／cobalance效度仍未验证。</p><p><a href="PLAN.md">设置与协议</a> · <a href="README.md">实际进展与限制</a> · <a href="../joint_deliberation_20261007/index.html">前一轮四段原始视频</a></p></section><section><h2>训练数据与模型</h2><p>{len(episodes)}条完整教师轨迹、480对输入／动作，训练360对、验证120对；完整init3作为验证，init4用于未见初始化测试。两场景、两种物品顺序，{audit["qualified_episodes"]}条通过释放稳定和运动核查。按同stem匹配，没有配对manifest。<a href="{link(DATA/"README.md")}">数据说明</a>。</p><p>使用已有中国源Qwen3-14B，BF16单卡LoRA适配；基础权重冻结。训练与推理都使用精简真实测量输入，约3000token，保留当前位置／接触／握持／公开消息与自己的意图。观察投影与权重学习共同变化，不能作单因素改善归因。</p><p>{learning}</p><img style="width:100%" alt="实际训练与验证回答损失，纵轴为对数" src="{link(TRAIN/"loss_curve.svg")}"><p><a href="{link(TRAIN/"training.jsonl")}">实际训练曲线原始记录</a> · <a href="https://huggingface.co/docs/peft/developer_guides/lora">LoRA官方文档</a>。损失曲线与闭环能力分开判断。</p></section>{''.join(panels)}<section><h2>结论边界</h2><p>教师成功不算学习模型成功；权重改变和损失下降不代替实际抓持、第二物品推进与释放稳定结果。40步检查为训练阶段诊断，不用于选择最终160步配置。闭环测试没有几何教师或固定动作队列。</p><p>当前是可靠伙伴的动作学习阶段，不能称为成熟Dynamic Human Policy HRC Benchmark。更多任务、真实动态接收物与原生VLA评测、完整人体及cobalance指标效度仍需推进。</p></section></main><script>const data={payload_json};for(const[key,r]of Object.entries(data)){{const v=document.getElementById(key),s=document.getElementById('state-'+key);function update(){{let f=r.frames[0];for(const a of r.frames)if(a.video_time_s<=v.currentTime)f=a;if(f.benchmark_time_s===null){{s.textContent='真实控制泊车，自主活动尚未开始。';return;}}let d=r.decisions[0];for(const a of r.decisions)if(a.time_s<=f.benchmark_time_s)d=a;s.textContent=`模拟 ${{f.benchmark_time_s.toFixed(2)}}秒 · 最新神经回答 ${{d.time_s.toFixed(2)}}秒\n自己选择的目标：${{JSON.stringify(d.goals)}}\n实际接收动作：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n原始解释：${{d.decision.reason}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();}}</script></html>'''
    (HERE/'index.html').write_text(html);(HERE/'facts.json').write_text(json.dumps({'research_goal_achieved':False,'training_complete':complete,'teacher_episodes':len(episodes),'episodes':facts},ensure_ascii=False,indent=2));print(json.dumps(facts,ensure_ascii=False))


if __name__=='__main__':main()
