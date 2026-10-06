"""两种学习机器人在基础参照和动态生成式伙伴中的实际运行报告。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
MODELS={'pi05':'π0.5','openvla':'OpenVLA'}
FAMILIES={'moving_receptacle':'移动接收盘：可以同时推进',
          'prepare_receptacle':'先准备接收盘：放置有前置条件',
          'shared_workspace':'共享空间：分别操作邻近物体'}


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def href(path):return '../../'+path.relative_to(ROOT).as_posix()
def video(path,key=None):
    attribute=f' data-audit="{key}"' if key else ''
    return f'<video controls preload="metadata" poster="{href(path/"preview.png")}" src="{href(path/"demo.mp4")}"{attribute}></video>'


def inputs(root, *, human=False, openvla=False):
    names=['summary.json','provenance.json','video_verification.json','model_execution_verification.json','placement_verification.json']
    if human:names+=['avatar_verification.json','human_feedback_verification.json']
    if openvla:names+=['preprocessing_verification.json']
    data={name:read(root/name) for name in names}
    assert data['video_verification.json']['status']=='verified'
    assert not data['provenance.json']['source_files_changed_during_run']
    assert data['provenance.json']['completion_criterion']=='released_stable'
    if openvla:assert data['preprocessing_verification.json']['pixel_exact_reconstruction']
    return data,[root/name for name in names]


def main():
    sources=[];evidence={};baseline_panels=[];panels=[];table=[];audits={};baseline_table=[];presence_panels=[];presence_table=[]
    for model,label in MODELS.items():
        root=RESULTS/'native_protocol_references'/model
        data,paths=inputs(root,openvla=model=='openvla');sources.extend(paths)
        metrics=data['summary.json']['episodes']
        baseline_table.append(f'<tr><td>{label}</td><td>{sum(m["task_success"] for m in metrics)}/{len(metrics)}</td><td>{data["placement_verification.json"]["physical_completion_verified_count"]}/{len(metrics)}</td><td>{data["model_execution_verification.json"]["motion_eligible_episode_count"]}/{len(metrics)}</td></tr>')
        evidence[f'{model}_reference']=data
        for metric in metrics:
            episode=root/f'task_{metric["task_id"]:02d}'/f'init_{metric["init_state_id"]:03d}'
            baseline_panels.append(f'<article><h3>{label}基础参照 · 场景{metric["task_id"]+1} / 初始状态{metric["init_state_id"]}</h3><p>{"完成" if metric["task_success"] else "未完成"}，模拟{metric["completion_time_s"]:.2f}秒，真实模型推理{metric["model_calls"]}次。</p>{video(episode)}<p><a href="{href(episode/"placement_evidence.jsonl")}">实际接触、释放和稳定记录</a></p></article>')
        presence_root=RESULTS/'native_presence_references'/model
        presence,paths=inputs(presence_root,openvla=model=='openvla');sources.extend(paths)
        assert read(presence_root/'avatar_verification.json')['qualified_count']==1
        sources.append(presence_root/'avatar_verification.json')
        presence_metric=presence['summary.json']['episodes'][0];evidence[f'{model}_presence']=presence
        presence_table.append(f'<tr><td>{label}</td><td>{int(presence_metric["task_success"])}/1</td><td>{presence["placement_verification.json"]["physical_completion_verified_count"]}/1</td></tr>')
        presence_panels.append(f'<article><h3>{label} · 人物在场但不行动</h3><p>{"完成" if presence_metric["task_success"] else "未完成"}，模拟{presence_metric["completion_time_s"]:.2f}秒；没有生成式人策略或人发出的反馈。加入人物、标记和接入后的同一物理场景，检查这些条件是否影响基础操作。</p>{video(presence_root/"task_02/init_000")}</article>')
        for family,family_label in FAMILIES.items():
            key=f'{model}_{family}';root=RESULTS/'native_model_hrc'/key
            data,paths=inputs(root,human=True,openvla=model=='openvla');sources.extend(paths)
            metric=data['summary.json']['episodes'][0];evidence[key]=data
            episode=root/'task_02/init_000'
            decisions=rows(episode/'human_policy_io.jsonl');audit=[]
            for row in decisions:
                public=json.loads(row['public_input'].split('\n',1)[1])
                audit.append({'time_s':row['time_s'],'decision':row['parsed_decision'],
                              'plan':row.get('generated_plan',[]),'execution':public['your_measured_execution'],
                              'wait_condition':row.get('wait_condition',''),'validation':row.get('command_validation')})
            audits[key]=audit
            intents=Counter(row['parsed_decision']['intent'] for row in decisions)
            valid=bool(data['model_execution_verification.json']['motion_eligible_episode_count']==1
                       and data['avatar_verification.json']['qualified_count']==1)
            physically_verified=data['placement_verification.json']['physical_completion_verified_count']==1
            assert not metric['task_success'] or physically_verified
            table.append(f'<tr><td>{label}</td><td>{family_label}</td><td>{int(metric["robot_goal_success"])}</td><td>{int(metric["human_goal_success"])}</td><td>{int(metric["task_success"])}</td><td>{"通过" if valid else "仅诊断"}</td></tr>')
            measured=metric['interaction_metrics']
            panels.append(f'''<article><h2>{label} · {family_label}</h2><p>结果：{"共同完成" if metric['task_success'] else "未共同完成"}。模拟{metric['completion_time_s']:.1f}秒，机器人真实推理{metric['model_calls']}次、人决定{metric['human_decisions']}次。人实际接受的意图：{escape('、'.join(f'{k} {v}次' for k,v in intents.items()))}。</p><p>人的公开工作：{escape(data['provenance.json']['human_public_work_requirement'])}</p>{video(episode,key)}<div class="audit" id="audit-{key}"></div><p>机器人EE平移{measured['robot_ee_motion_time_s']:.1f}s；人身体/指尖平移{measured['human_motion_time_s']:.1f}s；同时平移{measured['simultaneous_motion_time_s']:.1f}s；人的observe命令{measured['human_observe_command_time_s']:.1f}s。机器人EE与指尖最小距离{measured['minimum_ee_fingertip_distance_m']:.3f}m。这不是完整人体安全指标。</p><p>机器人释放稳定完成：{"已独立重建" if physically_verified else "未达成"}；运动与人物显示：{"通过当前核查" if valid else "未通过，保留诊断"}。</p><p><a href="{href(episode/'metrics.json')}">原始结果</a> · <a href="{href(episode/'human_policy_io.jsonl')}">人的真实模型输入输出</a> · <a href="{href(root/'placement_verification.json')}">独立物理完成重建</a></p></article>''')
            sources.extend(episode/name for name in ['metrics.json','human_policy_io.jsonl','human_execution_observations.jsonl'])
    audit_data=json.dumps(audits,ensure_ascii=False).replace('<','\\u003c')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>两种学习机器人与动态人类协作实测</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f2;color:#183844;font:17px/1.8 system-ui}}main{{max-width:1100px;margin:auto;padding:26px 20px;overflow-wrap:anywhere}}header{{background:#193f48;color:white;padding:28px;border-radius:14px}}section,article,details{{background:white;padding:24px;margin:24px 0;border-radius:14px}}h1{{font-size:clamp(25px,4vw,36px);line-height:1.4}}h2{{font-size:23px}}video{{width:100%;max-height:600px;background:#142430}}a{{color:#137775}}.audit{{background:#f2f6f5;border-left:4px solid #348b85;padding:16px;white-space:pre-wrap}}.notice{{background:#fff1da;padding:18px}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:650px}}th,td{{padding:10px;border-bottom:1px solid #d2dfdc;text-align:left}}@media(max-width:600px){{main{{padding:12px}}header,section,article,details{{padding:18px 15px}}}}</style><main>
<header><h1>两种学习机器人与动态生成式人的协作实测</h1><p>π0.5与OpenVLA都先通过原生基础操作参照，再检查静态人物在场和三类动态协作关系。机器人实际抓取/放置，人由本地Qwen自主选择当前意图；本批固定接口，保存16段真实Sim视频。</p></header>
<section><h2>本轮解决了什么</h2><p>上一轮第二种机器人只有接入诊断，图像处理未对齐；一些几何成功仍夹着碗。本轮对齐固定版本OpenVLA的JPEG编解码、缩放与中心裁剪，并保存模型真正消费的图像，独立逐像素重建。两种模型统一用接收盘接触、夹爪脱离且打开、物体与盘子低速稳定0.2秒的放置条件；原生几何关系单独不足以算完成。</p><p>基础参照只检查模型在配套技能和场景中是否能真正拿起、释放并完成放置；动态任务才检查人的自主行动给机器人带来的协调要求。推物依靠实际指尖受力，不改写物体坐标或吸附。</p></section>
<section><h2>设置与解释范围</h2><p>基础参照：2个空间摆放任务×2个初始状态，seed0。动态任务：task2/init0，合作型人，episode记忆；每条件一次。20Hz控制、最多20秒；π0.5每次执行最多10个原生动作，OpenVLA每步预测1个动作，按各自动作形式运行。人每1秒根据实际进展重新决定，不由评分器安排下一动作。</p><p>π0.5消费双相机与末端状态，OpenVLA消费外部相机与语言。人使用理想坐标与自己的执行反馈。推理时模拟时间暂停。人物为完整VICO骨骼蒙皮，身体仍不参与碰撞，操作仍是受力指尖代理。</p><p class="notice">本批不是公开LIBERO成绩复现或通用算法排名。只有两种模型、同一取放技能、一个人格和少量布局；基础任务属于模型配套任务域。机器人随机采样状态没有逐条件重置，人体、标记、语言和人动作共同变化，不能把差异只归因于某一个人策略因素。运动指标未校准成cobalance总分。</p></section>
<section><h2>基础操作参照</h2><div class="table-wrap"><table><tr><th>模型</th><th>任务完成</th><th>独立释放稳定重建</th><th>运动核查</th></tr>{''.join(baseline_table)}</table></div><p>基础操作已通过，动态任务的失败不再直接等同于机器人不会执行这一基础取放技能；失败原因仍需结合视频与人/机器人各自工作判定。</p></section>
<section><h2>人物与场景接入的影响</h2><div class="table-wrap"><table><tr><th>模型</th><th>静态人物条件完成</th><th>独立释放稳定重建</th></tr>{''.join(presence_table)}</table></div><p>π0.5通过静态人物条件，OpenVLA未通过。这意味着OpenVLA在后续动态任务的失败可能已包含人物外观、标记或场景接入影响，不能单独归因为不理解人的动态策略。该参照也不是只改变人体外观的严格消融；需要更多布局才能确定具体原因。</p></section>{''.join(presence_panels)}
<section><h2>三类动态协作要求与实际结果</h2><p><strong>移动接收盘：</strong>人移动盘子，机器人可同时放碗，需要跟随变化的接收位置。<strong>先准备盘子：</strong>人先移动接收盘，机器人可以先拿碗，但须等盘子准备好再释放；不能靠提前完成事后自动获得贡献。<strong>共享空间：</strong>人移动cookies到自己附近，机器人操作邻近碗/盘子；是附近物体的并行工作，尚未证明该布局必然需要冲突协商。</p><div class="table-wrap"><table><tr><th>模型</th><th>协调关系</th><th>机器人完成</th><th>人完成</th><th>共同完成</th><th>运动/显示</th></tr>{''.join(table)}</table></div></section>
<section><h2>如何看视频</h2><p>视频下方随播放/拖动显示当时的人模型选择、计划、理由和执行反馈。测量发生在当前命令执行前；发出命令不等于动作已经完成。每个片段都有独立控制、模型输入、时间轴与放置证据。平移时间以0.015m/s为阈值，不计夹爪开合或末端旋转；空间距离不是完整人体碰撞或安全证明。</p></section>
{''.join(panels)}<details><summary>展开8段基础操作参照视频</summary>{''.join(baseline_panels)}</details>
<section><h2>仍需推进</h2><p>当前能展示真实学习机器人与生成式人的动态共同场景，但成熟Benchmark仍未完成。下一阶段需要更多任务技能与布局、人的开放目标变化和角色协商、持续世界、真实手/身体接触、多人格效度与统计协议。当前没有把个别任务完成等同于cobalance能力已被验证。</p><p><a href="../native_dynamic_feedback/index.html">上一阶段：执行反馈与几何假阳性</a> · <a href="evidence.json">结果与来源摘要</a></p></section></main>
<script>const audits={audit_data};document.querySelectorAll('video[data-audit]').forEach(video=>{{let target=document.getElementById('audit-'+video.dataset.audit);function update(){{const history=audits[video.dataset.audit];let row=history[0];for(const item of history)if(item.time_s<=video.currentTime)row=item;const d=row.decision,e=row.execution,v=row.validation;target.textContent=`模拟 ${{row.time_s.toFixed(1)}}s · 实际接受 ${{d.intent}}\n目标：${{d.current_goal}}\n模型计划：${{row.plan.join(' → ')||'未输出'}}\n理由：${{d.reason}}\n等待条件：${{row.wait_condition||'未声明'}}\n命令验证：${{v?v.status+' '+v.errors.join(', '):'未记录'}}\n命令前实测：${{e.accepted_intent}} / ${{e.status}} / ${{e.motor_phase}}\n身体剩余距离：${{e.body_remaining_distance_m.toFixed(3)}}m${{e.object_remaining_xy_distance_m===undefined?'':'；物体剩余距离：'+e.object_remaining_xy_distance_m.toFixed(3)+'m'}}`;}}video.addEventListener('timeupdate',update);video.addEventListener('seeked',update);update();}});</script></html>'''
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps({'research_goal_achieved':False,'runs':evidence,
        'source_sha256':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sources}},ensure_ascii=False,indent=2))
    print(f'{HERE}/index.html：16段实际Sim视频')


if __name__=='__main__':main()
