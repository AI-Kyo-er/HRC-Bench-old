"""汇报动态人类执行反馈、不同协调关系与真实模型视频。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2/native_dynamic_feedback'
FAMILIES={'moving_receptacle':'移动接收盘：同时工作',
          'prepare_receptacle':'准备接收盘：放置前置条件',
          'shared_workspace':'整理共享空间：分别操作附近物体'}
PERSONAS={'cooperative':'合作倾向','assertive':'主动表达倾向'}


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def link(path):return '../../'+path.relative_to(ROOT).as_posix()
def read_requested(row):
    raw=row['raw_output']
    try:return json.loads(raw[raw.find('{'):raw.rfind('}')+1])
    except (ValueError,TypeError):return {'intent':'unparseable'}


def main():
    panels=[];table=[];evidence=[];sources=[];audits={}
    legacy_placement=read(RESULTS/'placement_verification.json')
    sources.append(RESULTS/'placement_verification.json')
    terminal_checks={Path(row['episode']).resolve():row for row in legacy_placement['episodes']}
    for family,label in FAMILIES.items():
        for persona,persona_label in PERSONAS.items():
            directory=RESULTS/f'{family}_{persona}'
            paths=[directory/name for name in ['summary.json','provenance.json','video_verification.json',
                                               'model_execution_verification.json','avatar_verification.json',
                                               'human_feedback_verification.json']]
            assert all(path.is_file() for path in paths)
            summary,provenance,video,execution,avatar,feedback=map(read,paths)
            assert video['status']=='verified' and not provenance['source_files_changed_during_run']
            assert feedback['status']=='verified'
            sources.extend(paths)
            metric=summary['episodes'][0]
            episode=directory/f'task_{metric["task_id"]:02d}'/f'init_{metric["init_state_id"]:03d}'
            decisions=rows(episode/'human_policy_io.jsonl')
            key=f'{family}_{persona}'
            feedback_enabled=provenance.get('human_action_validation_feedback',False)
            intents=Counter(row['parsed_decision']['intent'] for row in decisions)
            requested=Counter(read_requested(row).get('intent','missing') for row in decisions)
            rejected=sum(read_requested(row).get('intent')!=row['parsed_decision']['intent'] for row in decisions)
            audit=[]
            for row in decisions:
                visible=json.loads(row['public_input'].split('\n',1)[1])
                audit.append({'time_s':row['time_s'],'decision':row['parsed_decision'],
                              'requested':read_requested(row),
                              'validation':row.get('command_validation'),
                              'plan':row.get('generated_plan',[]),'wait_condition':row.get('wait_condition',''),
                              'execution':visible['your_measured_execution'],'robot':visible['robot_measured_motion']})
            audits[key]=audit
            measured=metric['interaction_metrics']
            eligible=execution['motion_eligible_episode_count']==1 and avatar['qualified_count']==1
            result_text='原生几何判定共同完成，但未验证物理释放' if metric['task_success'] else '未共同完成'
            terminal=terminal_checks[episode.resolve()]['terminal_contact_measurement']
            temporal=metric['task_contract']['premature_placements']
            table.append(f'<tr><td>{label}</td><td>{persona_label}</td><td>{int(metric["robot_goal_success"])}</td><td>{int(metric["human_goal_success"])}</td><td>{int(metric["task_success"])}</td><td>{"通过" if eligible else "仅诊断"}</td></tr>')
            panels.append(f'''<article><h2>{label} · {persona_label}</h2><p>{result_text}，模拟{metric['completion_time_s']:.1f}秒。π0.5推理{metric['model_calls']}次，Qwen决定{metric['human_decisions']}次：{escape('、'.join(f'{k} {v}次' for k,v in intents.items()))}。</p>
<p>接口阶段：{"带动作拒绝反馈" if feedback_enabled else "早期接口诊断：未反馈具体拒绝理由"}。原始请求：{escape('、'.join(f'{k} {v}次' for k,v in requested.items()))}；意图被接口改变{rejected}次。公开人的工作：{escape(provenance['human_public_work_requirement'])}</p>
<video controls preload="metadata" poster="{link(episode/'preview.png')}" src="{link(episode/'demo.mp4')}" data-audit="{key}"></video>
<div class="audit" id="audit-{key}" aria-live="polite"></div>
<p>机器人EE平移运动{measured['robot_ee_motion_time_s']:.1f}s；人运动{measured['human_motion_time_s']:.1f}s；同时运动{measured['simultaneous_motion_time_s']:.1f}s；双方位置均低速{measured['both_stationary_time_s']:.1f}s；人的observe命令{measured['human_observe_command_time_s']:.1f}s。</p>
<p>前置条件满足前出现原生放置几何关系的跳变{temporal}次。这是几何关系False→True的观测次数，可能含接触抖动，不表示{temporal}次完整的抓取—放置动作。</p>
<p>末帧夹爪与碗接触：{"仍有" if terminal['gripper_contact'] else "未检测到"}；夹爪开度{terminal['gripper_aperture_m']*1000:.1f}mm。旧运行未保存连续几何判定，没有验证持续释放稳定完成，原始几何成功不升级为物理完成。</p>
<p>EE与人指尖最小距离{measured['minimum_ee_fingertip_distance_m']:.3f}m；实际接触采样{measured['human_force_contact_samples']}个。资格：{"通过当前核查" if eligible else "未通过，仅保留诊断"}。这些距离与采样不是完整人体安全结论。</p>
<p><a href="{link(episode/'metrics.json')}">原始结果</a> · <a href="{link(episode/'human_policy_io.jsonl')}">原始人模型输入输出</a> · <a href="{link(episode/'human_execution_observations.jsonl')}">实际执行反馈</a> · <a href="{link(directory/'model_execution_verification.json')}">控制核查</a></p></article>''')
            evidence.append({'condition':key,'metrics':metric,'video':video,'execution':execution,'avatar':avatar,'feedback':feedback,
                             'human_intents':dict(intents),'requested_intents':dict(requested),'rejected_intent_count':rejected,
                             'action_validation_feedback_enabled':feedback_enabled,'eligible':eligible})
            sources.extend(episode/name for name in ['metrics.json','human_policy_io.jsonl','human_execution_observations.jsonl'])
    successes=sum(row['metrics']['task_success'] for row in evidence)
    qualified=sum(row['eligible'] for row in evidence)
    generated_count=sum(sum(row['human_intents'].values()) for row in evidence)
    baseline_root=ROOT/'results/continuous_v2/native_openvla_reference'
    baseline_summary=read(baseline_root/'summary.json')
    baseline_provenance=read(baseline_root/'provenance.json')
    baseline_execution=read(baseline_root/'model_execution_verification.json')
    baseline_video=read(baseline_root/'video_verification.json')
    assert baseline_video['status']=='verified' and not baseline_provenance['source_files_changed_during_run']
    baseline_metric=baseline_summary['episodes'][0]
    baseline_episode=baseline_root/'task_02/init_000'
    sources.extend(baseline_root/name for name in ['summary.json','provenance.json','model_execution_verification.json','video_verification.json'])
    baseline_panel=f'''<article><h2>第二种机器人架构：OpenVLA接入诊断</h2><p>中国ModelScope的LIBERO-Spatial微调权重已逐文件SHA256校验，官方实现权重载入没有缺失键、意外键或形状不匹配。真实原生Sim运行{baseline_metric['completion_time_s']:.1f}s、{baseline_metric['model_calls']}次推理，原始任务{"完成" if baseline_metric['task_success'] else "未完成"}。</p>
<video controls preload="metadata" poster="{link(baseline_episode/'preview.png')}" src="{link(baseline_episode/'demo.mp4')}"></video>
<p>此模型实际使用外部相机和语言，不使用接口兼容的腕部相机或末端状态。当前为SDPA推理、未执行官方默认的0.9面积中心裁剪；尚未完成官方预处理匹配和多初始状态基础参照。因此本段只证明真实权重、相机到原生动作的链路接通，不能据此判断OpenVLA能力或作为HRC比较。当前控制/视频独立核查{baseline_execution['episode_count']}条。</p><p><a href="{link(baseline_root/'provenance.json')}">真实模型与接口来源</a> · <a href="{link(baseline_root/'model_execution_verification.json')}">控制核查</a></p></article>'''
    released_root=ROOT/'results/continuous_v2/native_released_collaboration'
    released_summary=read(released_root/'summary.json')
    released_metric=released_summary['episodes'][0]
    released_episode=released_root/'task_02/init_000'
    released_check=read(released_root/'placement_verification.json')
    released_video=read(released_root/'video_verification.json')
    released_execution=read(released_root/'model_execution_verification.json')
    released_avatar=read(released_root/'avatar_verification.json')
    assert released_video['status']=='verified'
    assert not read(released_root/'provenance.json')['source_files_changed_during_run']
    sources.extend(released_root/name for name in ['summary.json','provenance.json','placement_verification.json',
                                                  'video_verification.json','model_execution_verification.json','avatar_verification.json'])
    physically_completed=bool(released_metric['task_success'] and released_check['physical_completion_verified_count']==1)
    released_panel=f'''<article><h2>修正几何假阳性：继续到释放并稳定</h2><p>上一条8.5秒片段在碗仍夹持时触发几何成功。这次控制持续进行，只有原生几何关系、碗接收盘接触、无夹爪接触且开度至少40mm、双方物体速度低于0.08m/s持续0.2秒，才记录机器人实际放置完成。判据只评估已发生的物理状态，不替模型打开夹爪或改变动作。</p><video controls preload="metadata" poster="{link(released_episode/'preview.png')}" src="{link(released_episode/'demo.mp4')}"></video><p>实际模拟{released_metric['completion_time_s']:.1f}秒，π0.5推理{released_metric['model_calls']}次、人模型决定{released_metric['human_decisions']}次。结果：{"严格物理判据下共同完成" if physically_completed else "严格物理判据下未共同完成"}。此运行不是旧片段的确定性续播；模型重新采样，不能把差异归因于某个单因素。</p><p><a href="{link(released_root/'placement_verification.json')}">独立释放与稳定重建</a> · <a href="{link(released_episode/'placement_evidence.jsonl')}">逐控制步物理完成证据</a></p></article>'''
    data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>动态人类执行反馈与协调关系实测</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:680px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 15px}}}}</style>
<main><header><h1>动态人类执行反馈与协调关系实测</h1><p>真实π0.5机械臂 + 本地Qwen生成式人 + 完整VICO人物。2个早期接口诊断、4个协调任务片段、1个严格物理完成实测，以及1个第二种机器人架构的接入诊断，共8段真实Sim视频。本轮重点是人能否根据实际动作进展调整自己的计划，以及这给机械臂带来的协调要求。</p></header>
<section><h2>为何推进这一轮</h2><p>上一轮人的输入持续写着机器人“正在放碗”，实际却可能已经停止。人的经历也会写“已返回”，但身体只返回到半途。本轮删除这种固定动作标签，提供实际EE速度、物体抬升、身体剩余距离、指尖目标和推物距离；模型写下的经历与已发生的测量分开保存。</p>
<p>参考<a href="https://github.com/dannymcy/coopera_code">COOPERA官方实现</a>中的人格、长期意图、任务分解和历史反思结构，增加Qwen自己生成并修订的多步计划和等待条件。程序只执行模型本次选择的一个动作，不自动照着计划逐步路由；observe仍可中断动作。这里尚未复现COOPERA的跨日个性化或真人效度验证。</p></section>
<section><h2>任务与设置</h2><p><strong>移动接收盘：</strong>人推盘子到自己附近，机器人放碗；盘子可在机器人行动时变化。</p><p><strong>准备接收盘：</strong>人先移盘子，机器人可先拿碗，但必须等盘子准备好再放；提前放置独立计数，不能事后自动获得贡献。</p><p><strong>整理共享空间：</strong>人把cookies物体移近自己，机器人处理附近的碗和盘子；双方分别操作邻近物体，没有额外规定谁先做。它扩展空间协调关系，但尚未证明该初始布局一定迫使双方发生冲突。</p>
<p>每种关系各运行合作、主动表达两种语言描述倾向。使用相同LIBERO task2/init0、seed41，最多20秒，20Hz控制；每0.5秒机器人重新观察，每1秒人重新决策。每个片段重新初始化且人记忆按episode隔离；这批不是连续世界或跨日实验。机器人看真实双相机与末端状态，人使用理想坐标及执行器反馈；双方不是同等视觉感知。推理时模拟时钟暂停。</p>
<p>前两个移动接收盘片段发现模型把物体名当成目标区域，接口拒绝后未反馈具体理由，保留为诊断；随后四个片段增加明确拒绝反馈与动作参数范围。全部片段独立保存来源摘要，运行期未改源码，但六个片段的接口版本并不相同。不能跨任务把结果差异解释为策略或人格提升。</p>
<p>身体仍为非碰撞运动学骨骼，操作由受力指尖推动；无物体吸附或控制期坐标改写。固定初始布局仅做任务覆盖实测，没有额外模型或数据下载。</p></section>
<section><h2>实际结果</h2><p>旧判据原始几何共同成功{successes}/6；{qualified}/6通过运动与显示核查，但这些核查没有证明释放完成。8.5秒几何成功片段末帧仍夹持，明确排除物理完成。共{generated_count}次真实人模型决定。下表保留原始字段，不作为已验证物理成功或排名；新增严格判据结果单独展示。</p><div class="table-wrap"><table><thead><tr><th>协调关系</th><th>人倾向</th><th>原始机器人完成</th><th>人完成</th><th>原始共同完成</th><th>运动/显示核查</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p class="notice">这些是探索性运行，不据此排名模型或比较人格效果。只有一个VLA、同一布局、每条件一次；机器人采样状态没有按条件重置，任务语言、反馈和计划接口同时变化，不能把与旧批次的差异归因为单一因素。生成式人的失败也会限制对机器人HRC能力的解释。</p></section>
<section><h2>如何观看视频与指标</h2><p>每个视频下方会随播放/拖动更新当时的人模型决定、计划、等待条件与实际执行距离。你可以核对“它说要做什么”和“身体及物体是否真的做到了”。所有视频均在真实运行时录制，并核对逐帧时间轴。</p><p>运动时间来自实际位置变化（速度阈值0.015m/s）；机器人只计EE平移，人计身体或指尖平移，不把手指开合、末端旋转计为平移运动。observe时长来自模型输出的持续区间。双方位置低速、并行平移和距离是诊断维度，不代表经过校准的协作质量或安全分数；没有计算单一cobalance排名。</p></section>
{''.join(panels)}
{released_panel}
{baseline_panel}
<section><h2>仍未达到的目标</h2><p>成熟Benchmark尚未完成：完整手部与人体接触动力学、多个先进机器人算法、更多技能与环境、开放目标变化、持续世界、多种人格验证和统计协议仍需推进。本轮先让实际执行成为人策略规划的依据，并用不同协调关系检验真实系统。</p><p><a href="../avatar_dynamic_hrc_20261006/index.html">上一轮完整人物与离返报告</a> · <a href="evidence.json">本批结果与来源摘要</a></p></section></main>
<script>const audits={data};document.querySelectorAll('video[data-audit]').forEach(video=>{{const target=document.getElementById('audit-'+video.dataset.audit);function update(){{const history=audits[video.dataset.audit];let row=history[0];for(const item of history)if(item.time_s<=video.currentTime)row=item;const e=row.execution,d=row.decision;target.textContent=`模拟 ${{row.time_s.toFixed(1)}}s · 模型请求 ${{row.requested.intent}} → 实际接受 ${{d.intent}}\n接口结果：${{row.validation?row.validation.status+" "+row.validation.errors.join(", "):"旧接口未记录详细拒绝反馈"}}\n当前目标：${{d.current_goal}}\n计划：${{row.plan.join(' → ')||'未输出'}}\n理由：${{d.reason}}\n等待条件：${{row.wait_condition||'未声明'}}\n实际动作：${{e.accepted_intent}} / ${{e.status}} / ${{e.motor_phase}}\n身体剩余距离：${{e.body_remaining_distance_m.toFixed(3)}}m${{e.object_remaining_xy_distance_m===undefined?'':'；物体剩余距离：'+e.object_remaining_xy_distance_m.toFixed(3)+'m'}}\n机器人EE实测速度：${{row.robot.eef_speed_m_s.toFixed(3)}}m/s`;}}video.addEventListener('timeupdate',update);video.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'conditions':evidence,
        'second_robot_diagnostic':{'metrics':baseline_metric,'provenance':baseline_provenance,'execution':baseline_execution},
        'released_stable_collaboration':{'metrics':released_metric,'placement':released_check,'execution':released_execution,'avatar':released_avatar},
        'source_sha256':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest() for path in sources}},ensure_ascii=False,indent=2))
    print(f'{HERE}/index.html：旧几何判定{successes}/6，严格物理共同完成{int(physically_completed)}/1；运动与显示核查旧批{qualified}/6')


if __name__=='__main__':main()
