"""从正式结果生成总体进展与自主人策略检查报告。"""
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=ROOT/'results/continuous_v2/neural_human_qualification_20261007'

def read(name):return json.loads((RUN/name).read_text())
def rows(name):return [json.loads(x) for x in (RUN/'human_activity'/name).read_text().splitlines() if x.strip()]

def main():
    gate=read('video_verification.json');assert gate['status']=='verified'
    check=read('qualification_verification.json');assert check['status']=='verified'
    assert read('personal_verification.json')['status']=='verified'
    result=read('summary.json')['episodes'][0]
    io=rows('human_policy_io.jsonl');plans=rows('human_planner_io.jsonl')
    counts=Counter(r['parsed_decision']['intent'] for r in io)
    contact=read('hand_robot_contact_verification.json')['episodes'][0]
    hand=read('hand_verification.json')['episodes']
    measurements=[{'time_s':r['time_s'],'action':r['parsed_decision'],
        'goals':r['personal_goal_state']['personal_targets'],
        'measured':json.loads(r['public_input'].split('\n',1)[1])['your_measured_execution']} for r in io]
    data=json.dumps(measurements,ensure_ascii=False).replace('<','\\u003c')
    base='../../results/continuous_v2/neural_human_qualification_20261007/'
    success='满足' if result['human_goal_success'] else '未满足'
    evaluable='可评分' if result['human_goal_evaluable'] else '不可评分（空目标不能算成功）'
    handtext='；'.join(f"{r['object_id']}：首次双指接触抬升 {r['first_bilateral_contact_lift_s']}秒，之后支撑释放 {r['first_released_support_contact_s']}秒" for r in hand)
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HRC Benchmark 实验进展</title><style>*{{box-sizing:border-box}}body{{background:#eef3f2;color:#193c43;margin:0;font:17px/1.8 system-ui}}main{{max-width:1120px;margin:auto;padding:24px 18px}}header{{background:#193d45;color:white;padding:28px;border-radius:16px}}section{{background:white;padding:24px;border-radius:14px;margin:22px 0}}h1{{font-size:clamp(26px,4vw,36px)}}h2{{font-size:24px}}video{{width:100%;background:#132d34;border-radius:8px}}a{{color:#13786e}}.notice{{padding:16px;background:#fff1d8;border-radius:8px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;min-width:780px;width:100%}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d1dfd8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef5f2;padding:16px}}button{{font:inherit;cursor:pointer;margin:8px;padding:7px 12px}}@media(max-width:600px){{main{{padding:12px}}section,header{{padding:18px 14px}}}}</style><main>
    <header><h1>从工程 Pilot 到真实模型的共同活动</h1><p>当前完成项、真实场景视频和未解决问题。阅读本页无需参与此前实验工作流。</p></header>
    <section><h2>我们在验证什么</h2><p>研究目标是：人的意图、工作安排与公开约定变化时，机器人能否理解变化、协调行动，并持续满足双方当前需求。既看任务是否完成，也看等待、让行、错误操作、目标失效和共同维持的时间。</p><p>最初 VC／Genesis Pilot 用手写策略验证连续时间轴和记录协议。当前核心实验已转为 LIBERO／MuJoCo 原生机械臂场景、真实学习模型输出和受力接触手。早期运动学吸附结果保留为工程记录；以下各阶段各自披露动作来源与物理设置。</p></section>
    <section><h2>当前系统怎样运行</h2><p>π0.5 读取实际外部／腕部相机、机器人本体状态和语言，输出原生7维末端控制。OpenVLA使用匹配的空间任务权重。可选 Qwen3-VL 视觉协调器读取公开对话、自身视觉与实际执行状态，选择执行或保持，并向人回应。</p><p>人使用本地 Qwen3-14B，每6秒推理当前较长期意图，每2秒选择动作；新公开消息也可触发推理。它可以调整私人目标、请求空间、抓取、放置或观察。当前物体几何感知是理想测量，身体为有贴图的骨骼显示，手是实际受力的双指代理。高层动作由模型选定，底层动作原语用控制阶段执行；不是完整学习的人体运动模型。</p><p>memory 包含模型生成的历史意图与解释；实际位置、接触和握持单独测量。评分在运行后重建，不用分数给模型路由下一项任务。私人目标不会直接提供给机器人。</p></section>
    <section><h2>已完成的主要实验</h2><div class="scroll"><table><tr><th>阶段与报告</th><th>完成内容</th><th>实测发现</th></tr>
    <tr><td><a href="../native_dynamic_hrc_20261006/index.html">原生模型与动态伙伴（12段视频）</a></td><td>校准原生观测／控制，并执行联合任务</td><td>存在经核验的共同完成片段；任务族和伙伴条件仍有限</td></tr>
    <tr><td><a href="../native_scene_catalog_20261007/index.html">跨物品、容器与抽屉（8段视频）</a></td><td>四种原生任务与无人物参照</td><td>无人物参照4/4；生成式伙伴条件仅抽屉原生任务成立，个人目标均未满足</td></tr>
    <tr><td><a href="../reflective_activity_20261007/index.html">分层意图／动作（9段视频）</a></td><td>四段60秒模型活动及独立抓放校准</td><td>模型个人目标均未完成；校准成功不能替代模型成绩</td></tr>
    <tr><td><a href="../grounded_reciprocal_20261007/index.html">可信反馈与双向协调（4段视频）</a></td><td>三类持续活动和视觉协调器共同运行</td><td>抽屉场景私人目标集合变化2次；四段严格共同完成均0</td></tr>
    </table></div><p>这些是不同配置的工程与行为实验，不能合并成模型排行榜或配对因果比较。全部保留失败、原始输入输出、控制、接触和完整视频。</p></section>
    <section><h2>本次收尾：人策略独立操作资格检查</h2><p>目的：检查生成式人策略能否在机器人不执行任务时，根据自己的偏好完成自主整理，避免直接把共同失败归因于机器人。使用同类桌面场景、init0／seed0；机器人先经80步实际控制泊车，然后保持零末端增量、夹爪打开。人没有指定动作清单、定时目标更新或外部安排；60秒／20Hz，世界与策略各初始化一次。</p><p>视频前4秒为实际泊车，随后60秒为自主活动；广角、外部相机与腕部相机均来自运行时直接渲染。播放器按仿真时间展示，并非模型推理的墙钟速度。</p>
    <video id="sim" controls playsinline preload="metadata" poster="{base}human_activity/preview.png" src="{base}human_activity/demo.mp4"></video><button data-time="4">自主活动开始</button><button data-time="24">自主活动20秒</button><button data-time="44">自主活动40秒</button><pre id="state"></pre>
    <p>人意图推理{len(plans)}次、动作推理{len(io)}次；机器人神经模型调用0次。动作分布：{escape('，'.join(f'{k} {v}次' for k,v in counts.items()))}。期末个人目标{success}，{evaluable}；新目标区间稳定满足{result['new_goal_intervals_satisfied']}个。手／机械臂几何接触累计{contact['hand_robot_contact_record_time_s']:.2f}秒。</p><p>{escape(handtext)}。这些接触／抬升见证不等于完成了选定目的地的放置。</p><p>机器人实际末端最大采样速度{check['robot_peak_measured_eef_speed_m_s']:.4f}m/s，末帧相对泊车位置位移{check['robot_eef_displacement_from_park_m']:.4f}m。零增量控制不能保证接触下机械臂绝对静止，也不能保证手的完整可达空间。</p><p><a href="{base}summary.json">实测结果</a> · <a href="{base}qualification_verification.json">控制与时钟核验</a> · <a href="{base}personal_verification.json">原始目标重建</a> · <a href="{base}video_verification.json">视频核验</a> · <a href="{base}human_activity/human_planner_io.jsonl">原始意图推理</a> · <a href="{base}human_activity/human_policy_io.jsonl">原始动作选择</a></p></section>
    <section><h2>结论与能力边界</h2><p>已经能运行真实学习机器人、生成式动态伙伴和连续接触场景，采集可复核的观测／动作数据与真实视频。动态接口及公开回应已经出现，尚未形成可靠的自主操作与持续共同完成。</p><div class="notice">成熟 Dynamic Human Policy HRC Benchmark 目标尚未完成。当前结果不证明先进VLA的HRC能力或cobalance能力，也不支持算法排名。人策略可靠性、动作可达性、模型分布适配、完整人体动力学与更广泛任务有效性仍需解决。</div><p>下一阶段应首先获得能在多场景独立操作的伙伴，再用匹配任务／初始化的共同活动与参照评测模型。避免继续把目标表可变、更多对话或一次教师校准成功当作研究贡献。</p></section></main>
    <script>const records={data};const v=document.getElementById('sim'),s=document.getElementById('state');function update(){{if(v.currentTime<4){{s.textContent='实际控制泊车；自主人策略尚未开始。';return;}}const t=v.currentTime-4;let d=records[0];for(const r of records)if(r.time_s<=t)d=r;s.textContent=`自主活动 ${{t.toFixed(2)}}秒 · 最新动作推理 ${{d.time_s.toFixed(2)}}秒\n私人目标：${{JSON.stringify(d.goals)}}\n选择：${{d.action.intent}} ${{d.action.object_id||''}} → ${{d.action.destination||''}}\n理由：${{d.action.reason||''}}\n实际阶段：${{d.measured.motor_phase}}；状态：${{d.measured.status||''}}；在手：${{d.measured.object_measured_in_hand||'无'}}`;}}v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);document.querySelectorAll('button').forEach(b=>b.onclick=()=>v.currentTime=Number(b.dataset.time));update();</script></html>'''
    (HERE/'index.html').write_text(html)
    print(json.dumps({'video_count':1,'human_goal_success':result['human_goal_success'],'research_goal_achieved':False},ensure_ascii=False))

if __name__=='__main__':main()
