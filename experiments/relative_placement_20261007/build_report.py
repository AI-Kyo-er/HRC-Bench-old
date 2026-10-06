"""以真实Sim视频呈现相对放置、不同物品校准及真实模型实验。"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path

import numpy as np

from hrc_pilot.video_verification import verify_result


ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'results/continuous_v2'
LABELS={'cream_cheese_1':'奶酪包 → 当前的碗','plate_1':'薄盘 → 个人区域',
        'wine_bottle_1':'酒瓶 → 个人区域','akita_black_bowl_1':'黑碗 → 个人区域'}


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def link(path):return '../../'+path.relative_to(ROOT).as_posix()
def time(value):return '未出现' if value is None else f'{value:.2f}秒'
def yes(value):return '成立' if value else '未成立'


def video(episode,events=(),identifier=''):
    buttons=''.join(f'<button type="button" data-video="{identifier}" data-seek="{t}">{escape(label)} · {t:.2f}秒</button>' for label,t in events if t is not None)
    return f'<video id="{identifier}" controls preload="metadata" playsinline poster="{link(episode/"preview.png")}" src="{link(episode/"demo.mp4")}"></video><div class="buttons">{buttons}</div>'


def fixed_region_final(episode):
    m=read(episode/'metrics.json');target=np.asarray(m['target_xyz']);trace=rows(episode/'trace.jsonl');obj=m['object_id']
    dwell=0.
    for previous,current in zip(trace,trace[1:]):
        position=np.asarray(current['objects'][obj]);dt=current['time_s']-previous['time_s']
        support=touch=False
        for c in current['contacts']:
            a,b=c['geom1'] or '',c['geom2'] or ''
            if b.startswith(obj+'_'):a,b=b,a
            if a.startswith(obj+'_'):
                support|=b=='table_collision'
                touch|=b.startswith(('gripper','human_left_finger','human_right_finger','human_palm','human_fingertip'))
        eligible=(np.linalg.norm(position[:2]-target[:2])<.025 and abs(position[2]-target[2])<.025
                  and support and not touch and np.linalg.norm(position-np.asarray(previous['objects'][obj]))/dt<.08)
        dwell=dwell+dt if eligible else 0.
    return bool(dwell>=.2-1e-9)


def main():
    panels=[];table=[];evidence={};hashes={};gate_count=0
    for obj,label in LABELS.items():
        root=RESULTS/'relative_hand_calibration'/obj;episode=root/'hand_validation'
        gate=verify_result(root,require_timeline=True)
        if gate['status']!='verified':raise RuntimeError(f'正式视频门槛未通过：{root}')
        gate_count+=gate['verified_episode_count']
        m=read(episode/'metrics.json');hand=read(root/'hand_verification.json')['episodes'][0]
        avatar=read(root/'avatar_verification.json');provenance=read(root/'provenance.json')
        assert not provenance['source_files_changed_during_run']
        relative=obj=='cream_cheese_1'
        score=read(root/'multi_actor_release_verification.json')['episodes'][0] if relative else None
        final=score['final_all_actor_released_stable'] if score else fixed_region_final(episode)
        note=('物体真实支撑关系成立，但手指受碗边约束，张手阶段未结束；原始评分还要求机械臂空夹张开，因此原始分数为假。'
              if relative else '真实抓放并完成个人区域支撑关系。' if final else '未形成双指抬起，仍在下降阶段；不计作操作能力已具备。')
        table.append(f'<tr><td>{label}</td><td>{time(hand["first_bilateral_contact_lift_s"])}</td><td>{time(hand["first_released_support_contact_s"])}</td><td>{yes(final)}</td><td>{escape(m["terminal_phase"])}</td></tr>')
        events=[('双指抬起',hand['first_bilateral_contact_lift_s']),('抓取后支撑释放',hand['first_released_support_contact_s'])]
        panels.append(f'<article><h3>{label} · 执行器校准</h3><p>{note}</p>{video(episode,events,obj)}<p>25秒／20Hz；真实手峰速{hand["human_peak_speed_m_s"]:.3f}m/s，物体最大抬升{m["maximum_object_lift_m"]*100:.2f}cm；运动与显示资格{yes(hand["motion_qualified"] and avatar["status"]=="verified")}。</p><p><a href="{link(root/"hand_verification.json")}">接触与释放审计</a> · <a href="{link(episode/"teacher_commands.json")}">校准命令</a> · <a href="{link(root/"video_verification.json")}">视频核验</a></p></article>')
        evidence[obj]={'metrics':m,'hand':hand,'avatar':avatar,'video':gate,'provenance':provenance,'final_physical_relation':final}
        if relative:evidence[obj]['multi_actor_release']=score
        for path in [episode/'metrics.json',episode/'trace.jsonl',root/'provenance.json',episode/'demo.mp4',episode/'video_timeline.json']:
            hashes[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes()).hexdigest()
    root=RESULTS/'relative_model_hrc/food_into_bowl';episode=root/'task_06/init_000'
    gate=verify_result(root,require_timeline=True)
    if gate['status']!='verified':raise RuntimeError('模型运行真实视频门槛未通过')
    gate_count+=gate['verified_episode_count']
    names=['summary.json','provenance.json','model_execution_verification.json','avatar_verification.json',
           'human_feedback_verification.json','personal_verification.json','prompt_token_verification.json',
           'relative_geometry_verification.json','multi_actor_release_verification.json','hand_verification.json','scene_integrity_verification.json']
    model={name:read(root/name) for name in names};m=model['summary.json']['episodes'][0]
    assert not model['provenance.json']['source_files_changed_during_run']
    for name in ['model_execution_verification.json','avatar_verification.json','human_feedback_verification.json','personal_verification.json','relative_geometry_verification.json']:
        assert model[name]['status']=='verified'
    human=rows(episode/'human_policy_io.jsonl');score=model['multi_actor_release_verification.json']['episodes'][0]
    modes=Counter(d['parsed_decision']['intent'] for d in human)
    relative_actions=[{'time_s':d['time_s'],'object_id':d['parsed_decision']['object_id'],'destination':d['parsed_decision']['destination']}
                      for d in human if d['parsed_decision']['intent']=='place' and (d['parsed_decision']['destination'] or '').startswith('on:')]
    model['actual_relative_place_decisions']=relative_actions;model['video']=gate;evidence['learned_models']=model
    audit=[{'time_s':d['time_s'],'decision':d['parsed_decision'],'goals':d['personal_goal_state'],
            'execution':json.loads(d['public_input'].split('\n',1)[1])['your_measured_execution']} for d in human]
    data=json.dumps(audit,ensure_ascii=False).replace('<','\\u003c')
    timeline=json.dumps(read(episode/'video_timeline.json')['frames'],ensure_ascii=False)
    robot_first=score['first_all_actor_released_stable_s']
    integrity=model['scene_integrity_verification.json']['episodes'][0]
    losses=[o for o in integrity['objects'] if o['first_sustained_below_table_clearance_s'] is not None]
    main_video=video(episode,[('原生物体关系稳定',robot_first)]+[(o['object_id']+'离开桌面',o['first_below_table_clearance_s']) for o in losses],'model-video')
    facts=(f'真实π0.5推理{m["actual_vla_model_calls"]}次、实际OSC动作{m["executed_native_actions"] if "executed_native_actions" in m else model["model_execution_verification.json"]["native_actions"]}个；人模型{len(human)}次决定。'
           f'原生目标首次释放稳定{time(robot_first)}、期末{yes(score["final_all_actor_released_stable"])}；人的当前个人目标{yes(m["human_goal_success"]) if m["human_goal_evaluable"] else "无可测目标，不计作人任务失败"}。'
           f'人的可观察目标集合改变{m["personal_evidence"]["observable_target_set_changes"]}次；实际相对放置决定{len(relative_actions)}次。')
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真实场景视频 · 相对放置与操作边界</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#eef3f1;color:#193c43;font:17px/1.8 system-ui}}main{{max-width:1080px;margin:auto;padding:24px 18px;overflow-wrap:anywhere}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section,article{{background:white;padding:24px;margin:22px 0;border-radius:14px}}h1{{font-size:clamp(27px,4vw,36px);line-height:1.4}}h2{{font-size:25px}}h3{{font-size:21px}}video{{width:100%;max-height:600px;background:#132d34;border-radius:8px}}a{{color:#13786e}}button{{font:inherit;cursor:pointer;background:#e7f2ee;color:#214840;border:1px solid #9dbbb1;border-radius:6px;padding:7px 12px;margin:7px 8px 0 0}}button:focus-visible{{outline:3px solid #ce952d}}.notice{{background:#fff1d8;padding:17px;border-radius:8px}}.audit{{white-space:pre-wrap;background:#eff5f2;padding:17px;border-left:4px solid #368f7c}}.scroll{{overflow-x:auto}}table{{width:100%;min-width:730px;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d1dfd8}}summary{{cursor:pointer;font-weight:600}}@media(max-width:600px){{main{{padding:12px}}header,section,article{{padding:18px 14px}}}}</style>
<main><header><h1>看见真实抓放，也看见失败发生在哪里</h1><p>本批新增相对接收物放置工具、四种物品的执行器校准，以及真实π0.5与生成式人策略的共同活动。五段完整运行时Sim视频，逐帧时间轴和解码核验全部通过。</p></header>
<section><h2>为什么做这轮实验</h2><p>上一批发现，人将固定bowl_home坐标当成“把奶酪放入碗”；容器已经移动时，初始坐标也不会随它变化。本轮增加on:接收物体工具，从当前碰撞几何读取支撑位置，并考虑抓持时手与物体底面的偏移。它表达接触支撑放置，不保证物体完整位于容器内部。</p><p>人的目标和当前工具仍由真实Qwen选择；接近、闭指和张手等低层运动阶段只执行已选动作，不按评分器给人挑任务。机器人使用本地学习权重和原生动作，没有教师接管、吸附、焊接或物体坐标搬写。</p><p>每段是仿真运行当时直接渲染的相机视频。默认按1倍模拟时间播放；模型推理时模拟时钟暂停，因此视频长度不是实际计算耗时。可以拖动查看，并用事件按钮定位。</p></section>
<section><h2>先看真实模型怎样共同活动</h2><p>{facts}</p><p>设置：LIBERO_goal任务6、init0/seed0；持续40秒／20Hz。π0.5读取外部和腕部相机、8维本体与公开语言，每块最多10步；Qwen3-14B每2秒生成自己的目标与一个当前动作。人的偏好私有，没有固定人任务或定时目标更新。</p>{main_video}<div id="model-audit" class="audit"></div><p>人动作：{escape('、'.join(f'{key} {count}次' for key,count in modes.items()))}。公开提案{m['personal_evidence']['public_negotiation_proposals']}条。工具可用与模型实际使用分开统计，提案不等于对方接受。</p><p class="notice">目标完成后世界仍持续：26.60秒酒瓶离开桌面，最终落到地面附近；其采样峰速4.89m/s。跌落前有机械臂夹指接触见证，但不是唯一因果证明。奶酪放置成功不能掩盖另一物品损失；这是连续场景的重要附带结果。手部、目标物和人物显示的既有运动核验通过，不代表所有库存物品都没有高速运动。<a href="{link(root/'scene_integrity_verification.json')}">全部库存的物品损失审计</a>。</p><p><a href="{link(episode/'human_policy_io.jsonl')}">人模型原始输入输出</a> · <a href="{link(root/'model_execution_verification.json')}">真实模型输入与控制核验</a> · <a href="{link(root/'multi_actor_release_verification.json')}">双方释放审计</a> · <a href="{link(root/'relative_geometry_verification.json')}">相对几何重建</a></p></section>
<section><h2>操作库有多可靠</h2><p>以下命令来自校准教师，机械臂原地；用于区分人模型选择失败与执行器能力不足，不能当作学习人策略、HRC成功率或专家模型排名。</p><div class="scroll"><table><tr><th>物品／目的地</th><th>双指抬起</th><th>抓取后释放至支撑</th><th>期末实际目标关系</th><th>执行器末阶段</th></tr>{''.join(table)}</table></div><p>薄盘的下降到位误差从10毫米收紧至2毫米；这使本次薄盘操作完成，但黑碗和酒瓶仍被下降接触阻挡，不能说泛化操作库已建成。奶酪物理关系成立时，手指开口仍受碗边限制；实际放下与控制器结束不是同一个事件。</p></section>{''.join(panels)}
<section><h2>完成怎么判断，结论有哪些限制</h2><p>物体放置的独立多主体审计要求：原生几何关系成立、与接收物真实接触、双方手部都不再接触、两个物体速度低于0.08m/s并连续稳定0.2秒。保留旧评分；旧评分还要求机械臂夹爪张开，会错误排除“人已放下、机械臂在别处空夹闭合”的情况。本批修订审计是事后重算，未把成绩反馈给模型，也未改写运行时原始结果。</p><p class="notice">当前仍是接触双指手代理与人物骨骼显示，尚非完整五指及身体动力学；人读取理想几何，机器人读取真实Sim相机。个人目标仍限于固定区域，可执行相对工具不等于完整关系目标规划。单次模型实验与混合校准来源不足以证明HRC/cobalance能力、动态偏好真实性或任何算法排名；完整Benchmark目标未完成。</p><p>首次相对校准在8.45秒因旧反馈仍查询固定区域而中断，未产生完整轨迹／时间轴；诊断视频保留，未混入五段正式视频。修复后的奶酪校准及模型实验各自源文件冻结，并单独保存来源哈希。</p><details><summary>查看未完成的接口诊断片段（8.45秒，缺完整审计轨迹）</summary><video controls preload="metadata" src="../../results/continuous_v2/relative_hand_calibration/cream_cheese_1_interface_failure/hand_validation/demo.mp4"></video></details></section>
<section><h2>完整设置与已有进展</h2><p><a href="README.md">本批完整说明</a> · <a href="evidence.json">结果、源哈希与视频核验</a> · <a href="../native_scene_catalog_20261007/index.html">四类厨房任务／八段真实视频</a> · <a href="../articulated_hrc_20261007/index.html">高台抓放与共同活动／四段真实视频</a></p><p>正式轨迹按同stem导出双相机、本体、公开语言与实际模型动作；失败保留，校准教师不混入模型数据。仍需推进高层意图反思与动作生成的分离、不同外形的可靠操作、更丰富活动和模型覆盖。</p></section></main>
<script>const decisions={data},frames={timeline};const v=document.getElementById('model-video'),out=document.getElementById('model-audit');function update(){{let f=frames[0];for(const r of frames)if(r.video_time_s<=v.currentTime)f=r;const t=f.benchmark_time_s;let d=decisions[0];for(const r of decisions)if(r.time_s<=t)d=r;out.textContent=`模拟 ${{t.toFixed(2)}}秒 · 人决定 ${{d.time_s.toFixed(2)}}秒\n当前动作：${{d.decision.intent}} ${{d.decision.object_id||''}} → ${{d.decision.destination||''}}\n自己选择的目标：${{JSON.stringify(d.goals.personal_targets)}}\n公开说：${{d.decision.message}}\n理由：${{d.decision.reason}}\n实际阶段：${{d.execution.motor_phase}}；测得在手：${{d.execution.object_measured_in_hand||'无'}}；执行反馈：${{d.execution.motor_failure||'无异常反馈'}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);update();document.querySelectorAll('button[data-seek]').forEach(b=>b.addEventListener('click',()=>{{document.getElementById(b.dataset.video).currentTime=Number(b.dataset.seek);}}));</script></html>'''
    for path in [*(root/name for name in names),episode/'human_policy_io.jsonl',episode/'trace.jsonl',episode/'demo.mp4',episode/'video_timeline.json']:
        hashes[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes()).hexdigest()
    evidence['formal_video_count']=gate_count;evidence['research_goal_achieved']=False;evidence['source_sha256']=hashes
    (HERE/'index.html').write_text(html)
    (HERE/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps({'report':str(HERE/'index.html'),'formal_videos':gate_count,'model_facts':facts},ensure_ascii=False))


if __name__=='__main__':main()
