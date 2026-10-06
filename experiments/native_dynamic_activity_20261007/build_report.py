"""公开动态工作要求、实际生成决定、完整Sim视频与分阶段物理结果。"""
from html import escape
from pathlib import Path
from hashlib import sha256
import json

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2/native_dynamic_activity'
LABELS={'receiver_changes':'接收盘位置要求反复变化','priority_changes':'人的整理对象与优先级变化','interruption_return':'临时事务、暂离与返回'}


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def link(p):return '../../'+p.relative_to(ROOT).as_posix()
def fmt(v):return '未发生' if v is None else f'{v:.2f}s'


def main():
    panels=[];summary=[];audit={};evidence={};hashes={};findings=[]
    for profile,label in LABELS.items():
        root=RESULTS/profile;episode=root/'task_02/init_000'
        names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json',
               'avatar_verification.json','human_feedback_verification.json','placement_verification.json','activity_verification.json','prompt_token_verification.json']
        d={n:read(root/n) for n in names}
        for name in names:
            if name=='prompt_token_verification.json':assert d[name]['status'] in {'verified_no_truncation','truncation_detected'}
            elif name=='placement_verification.json':assert d[name]['status']=='audited'
            elif name not in {'summary.json','provenance.json','avatar_verification.json'}:assert d[name]['status']=='verified'
        assert not d['provenance.json']['source_files_changed_during_run']
        assert d['avatar_verification.json']['qualified_count']==1
        token_note=f"π0.5完整token最大长度{max(e['max_tokens'] for e in d['prompt_token_verification.json']['episodes'])}/{d['prompt_token_verification.json']['token_limit']}，截断调用{d['prompt_token_verification.json']['truncated_calls']}次。"
        m=d['summary.json']['episodes'][0];activity=m['dynamic_activity']
        valid=d['model_execution_verification.json']['motion_eligible_episode_count']==1
        human=rows(episode/'human_policy_io.jsonl');trace=rows(episode/'trace.jsonl')
        audit[profile]={'decisions':[{'time_s':h['time_s'],'decision':h['parsed_decision']} for h in human],
                        'updates':read(episode/'activity_plan.json')['updates'],'trace':trace,
                        'regions':read(episode/'activity_plan.json')['regions']}
        place=rows(episode/'placement_evidence.jsonl')
        robot_stage=[]
        for stage in activity['stages']:
            samples=[r for r in place if stage['time_s']<r['time_s']<=stage['end_s']]
            reached=next((r['time_s'] for r in samples if r['released_stable_placement']),None)
            robot_stage.append({'start_s':stage['time_s'],'first_released_stable_s':reached,
                                'terminal_released_stable':bool(samples and samples[-1]['released_stable_placement'])})
        evidence_robot='；'.join(f"{r['start_s']:.0f}s要求后：首个合法放置{fmt(r['first_released_stable_s'])}，阶段末{'仍成立' if r['terminal_released_stable'] else '不成立'}" for r in robot_stage)
        stages=activity['stages']
        findings.append(f'<li>{label}：实际完成{activity["physically_completed_stage_count"]}/{len(stages)}阶段。'+
                        '；'.join(f'{s["label"]}：匹配动作延迟{fmt(s["first_matching_action_latency_s"])}，物理完成延迟{fmt(s["physical_completion_latency_s"])}，旧/其他任务推操作{s["obsolete_or_other_task_push_decisions"]}次' for s in stages)+'</li>')
        stage_rows=''.join(f'<tr><td>{s["time_s"]:.0f}–{s["end_s"]:.0f}s<br>{escape(s["label"])}</td><td>{fmt(s["first_matching_action_latency_s"])}</td><td>{fmt(s["physical_completion_latency_s"])}</td><td>{s["obsolete_or_other_task_push_decisions"]}/{s["push_decisions"]}</td></tr>' for s in activity['stages'])
        summary.append(f'<tr><td>{label}</td><td>{activity["physically_completed_stage_count"]}/{len(activity["stages"])}</td><td>{int(m["human_goal_success"])}</td><td>{int(m["robot_goal_success"])}</td><td>{int(m["task_success"])}</td><td>{m["actual_vla_model_calls"]}</td></tr>')
        panels.append(f'''<article><h2>{label}</h2><p>{escape(token_note)}</p><p>真实π0.5调用{m['actual_vla_model_calls']}次，人模型决定{len(human)}次，原生控制{m['native_actions']}步；运动资格{'通过' if valid else '未通过，以下仅作诊断'}。人的当前最终目标{'完成' if m['human_goal_success'] else '未完成'}，机器人{'完成' if m['robot_goal_success'] else '未完成'}。</p><video data-profile="{profile}" controls preload="metadata" poster="{link(episode/'preview.png')}" src="{link(episode/'demo.mp4')}"></video><div class="audit" id="audit-{profile}"></div><div class="scroll"><table><tr><th>公开工作要求</th><th>首个匹配动作延迟</th><th>实际完成延迟</th><th>旧/其他任务推操作</th></tr>{stage_rows}</table></div><p>机器人实际放置关系：{escape(evidence_robot)}。</p><p>推操作比值分母仅为push决定，观察或等待不计作错误。实际完成时间只对应本阶段要求，有接触与稳定证据；已取消任务的成功不补记到最终成绩。</p><p><a href="{link(episode/'activity_evidence.json')}">完整动态指标</a> · <a href="{link(episode/'human_policy_io.jsonl')}">人模型原始输入输出</a> · <a href="{link(episode/'model_calls.jsonl')}">π0.5实际请求与输出</a> · <a href="{link(root/'activity_verification.json')}">公开要求与实际输入核查</a></p></article>''')
        evidence[profile]={**d,'robot_placement_by_public_work_phase':robot_stage}
        for p in [*(root/n for n in names),*(episode/n for n in ['activity_plan.json','activity_events.json','activity_evidence.json','human_policy_io.jsonl','model_calls.jsonl'])]:hashes[str(p.relative_to(ROOT))]=sha256(p.read_bytes()).hexdigest()
    # A trace subset suffices for video audit, excluding private grade and actuator detail.
    for values in audit.values():values['trace']=[{k:r[k] for k in ['time_s','objects','human_position','human_hand_position','robot_ee']} for r in values['trace']]
    data=json.dumps(audit,ensure_ascii=False).replace('<','\\u003c')
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>动态人类工作要求 · 持续世界实测</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:650px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style><main><header><h1>人在工作途中改变要求，机器人还能协作吗？</h1><p>三类持续任务，三段完整真实Sim视频。每条45秒，物体、人的动作、模型记忆和机器人状态始终留在同一个世界里。工作要求会更新，具体动作仍由生成式人和真实具身模型决定。</p></header>
<section><h2>这轮新增什么</h2><p>先前实测主要是固定分工的推盘与放碗。这次加入同一接收盘反复迁移、不同物体的工作优先级变化、暂离返回和未完成工作的衔接。新要求只更新公开工作板，不替模型写current_goal，不自动调用推物、返回或抓取动作，也不依据分数切换策略。</p><p>任务分别为：盘到绿色→回蓝色原位→再到绿色；饼干到橙色→盘优先到绿色→饼干回紫色原位；整理饼干→临时事务暂离→返回→准备接收盘。机器人持续负责把桌面中央黑碗放到盘中。标记位置来自初始布局，运行途中既不搬动物体也不改标记位置。</p><p>设置：原生LIBERO task2/init0/seed0；π0.5读外部/腕部相机、8维本体状态及当前公开人工作/消息，直接输出7维末端增量；Qwen3-14B读公开几何和自身反馈，自主选择推、观察、让行、离返。合作倾向，episode记忆；20Hz物理控制、π动作块最多10步，人默认每2秒及新要求时推理。推理期间模拟时钟暂停。</p><p class="notice">公开变化时刻预先声明，保证测试可复现；这是外部工作要求变化下的生成式策略实测。人自身开放目标、完整角色协商和真实手部抓持仍未实现。人体是非碰撞骨骼显示与受力指尖代理。不能把本批称为完全开放的人类仿真，或原始π0.5官方排名。</p></section>
<section><h2>结果与证据边界</h2><div class="scroll"><table><tr><th>任务</th><th>曾完成阶段</th><th>人最终完成</th><th>机器人最终完成</th><th>最终共同完成</th><th>VLA实际调用</th></tr>{''.join(summary)}</table></div><p>动作选择响应、实际阶段完成与最终共同完成分开统计。新要求下仍选择其他物体/旧目的地的push单独列出；等待、退让不能仅凭类别判成失败。当前结果描述真实系统行为，无匹配控制、单布局和单合作倾向，不能给出因果提升、一般算法排名或cobalance效度结论。</p></section>
<section><h2>这批实际发生了什么</h2><ul>{''.join(findings)}</ul><p>优先级变化任务首阶段的公开工作板正确写着cookies_1→cookies_ready；Qwen却反复推plate_1→near_human，8次操作都未匹配当前要求。它在15秒与30秒正确切换选择，但物理执行仍未完成。初始输入还保留了已撤销的旧推盘安排，系统提示也以推盘为默认例子；这一历史与提示混杂需要披露，不能把首阶段错误直接认定为一般的人类模型能力缺陷。本批暴露人类模拟策略的任务遵从问题，不能把共同失败全归为机器人缺乏HRC能力。</p><p>暂离返回任务中，人在5.8秒完成饼干整理、14.65秒实际清离；但16秒重新选择推饼干，提前回到工作台。因此18秒阶段很快满足返回位置，不能解释为模型正确选择了return。30秒要求改为推盘后，它仍持续选择饼干，共8次旧目标操作。这里展示了动作关系、自身目标与公开要求之间的持续不一致。</p></section>{''.join(panels)}<section><h2>怎么判断完成</h2><p>人的推物需物体中心处于25mm目标范围、支撑高度误差小于25mm、速度低于0.08m/s稳定0.2秒，且本阶段已有实际指尖接触。身体暂离与返回按实际位置和持续时间判定，未真正离开不能补算返回。机器人放置需原生几何成立、碗盘实际接触、夹爪释放并持续稳定；已取消或后来被破坏的关系不计入最终共同成功。</p><p>视频是运行时场景录制，逐帧时间轴与真实物理时钟核验；模型请求、原始输出和实际控制另行重建。核验通过表示记录一致，不意味着模型完成或理解了任务。<a href="evidence.json">来源及核查结果</a> · <a href="README.md">完整实验说明</a> · <a href="../../datasets/native_dynamic_activity/dataset_metadata.json">270组实测观测与2700个动作的数据覆盖</a></p></section>
<section><h2>研究方向与仍需实现的部分</h2><p>参考<a href="https://github.com/dannymcy/coopera_code/blob/main/HUMAN.md">COOPERA人类仿真</a>对心理倾向和长期意图的组织方向，本轮先让人的公开工作要求真实变化，并让动作与记忆连续。后续仍需扩大操作技能、场景、人格与算法覆盖，并实现双方实际协商产生的目标和分工；当前三项任务没有覆盖完整交互组合。<a href="../grounded_coordination_20261007/index.html">上一批固定分工的视觉协调实测</a></p></section></main>
<script>const runs={data};document.querySelectorAll('video[data-profile]').forEach(video=>{{let box=document.getElementById('audit-'+video.dataset.profile);const run=runs[video.dataset.profile];function update(){{let work=run.updates[0],decision=run.decisions[0],state=run.trace[0];for(const w of run.updates)if(w.time_s<=video.currentTime)work=w;for(const d of run.decisions)if(d.time_s<=video.currentTime)decision=d;for(const t of run.trace)if(t.time_s<=video.currentTime)state=t;let distance='身体离返要求';if(work.object_id){{let p=state.objects[work.object_id],g=run.regions[work.destination];distance=`当前物体距目标：${{(Math.hypot(p[0]-g[0],p[1]-g[1])*1000).toFixed(1)}}mm（可见范围25mm）`;}}box.textContent=`公开要求 ${{work.time_s.toFixed(0)}}s · ${{work.label}}\n${{work.instruction}}\n人模型 ${{decision.time_s.toFixed(2)}}s · ${{decision.decision.intent}} ${{decision.decision.object_id||''}} → ${{decision.decision.destination||''}}\n自主目标：${{decision.decision.current_goal||''}}\n说：${{decision.decision.message}}\n理由：${{decision.decision.reason}}\n${{distance}}\n实际身体y：${{state.human_position[1].toFixed(3)}}m；指尖y：${{state.human_hand_position[1].toFixed(3)}}m`;}}video.addEventListener('timeupdate',update);video.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(page)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'runs':evidence,'source_sha256':hashes},ensure_ascii=False,indent=2))
    print(HERE/'index.html')


if __name__=='__main__':main()
