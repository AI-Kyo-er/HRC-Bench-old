"""发布真实开门参考视频及已核对的初态，明确控制与协调边界。"""
from collections import Counter
from html import escape
import json
import os
from pathlib import Path

from hrc_pilot.joint_video_captions import ensure_research_captions


def build():
    output=Path('experiments/drawer_operation_floor_20261009')
    root=Path('results/continuous_v2/drawer_operation_floor_init2_seed113_20261009')
    audit=json.loads((root/'interaction_verification.json').read_text())
    video=json.loads((root/'independent_video_verification.json').read_text())
    if audit['status']!='verified' or video['status']!='verified':raise ValueError('要求完整输入/执行/视频核验')
    match=json.loads((root/'initial_state_comparison.json').read_text())
    process=json.loads((root/'joint_process_evidence.json').read_text())
    summary=json.loads((root/'summary.json').read_text())['episodes'][0]
    calls=[json.loads(x) for x in (root/'episode/model_calls.jsonl').read_text().splitlines() if x.strip()]
    counts=Counter(x['action_source'] for x in calls)
    caption=ensure_research_captions(root)
    links=[('summary.json','完整终态'),('provenance.json','执行与源码'),('interaction_verification.json','实际输入/动作核查'),
           ('initial_state_comparison.json','初始XML与状态比较'),('joint_process_evidence.json','开度与真实过程'),
           ('operation_witness.json','开门时实际VLA控制来源'),
           ('independent_video_verification.json','801帧视频核查')]
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>抽屉基本操作前提：同初态真实参考</title><style>body{font:16px/1.7 system-ui;background:#edf2f5;color:#182536;margin:0;overflow-wrap:anywhere}main{max-width:1000px;margin:auto;padding:24px}section{background:white;padding:20px;border-radius:12px;margin:16px 0}video{width:100%;background:#10151b}a{color:#155aa7}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>抽屉基本操作前提：同初态真实参考</h1><section><p>动态例开度全程0。此40模拟秒参考检查基本开门是否可兑现：固定人清盘，真实π0.5执行原生开中抽屉指令；等待和后续笛卡尔清场为明确参考控制，不计神经人或双向协作成绩。</p><p>保存初始XML逐字一致，qpos、qvel、物体、末端、手及身体状态差异均0。之后人策略、指令选择、时序和时长不同；不能将差异单独归因某个协调机制。</p><p>21.55秒原生开门关系成立，最大开度约0.161m。开门有真实VLA见证，证明此初态存在可执行参考，不证明动态轨迹每个后续状态同样可恢复。38.2秒原安排物理观察成立，40秒已观察到存物包含，但参考宏未全部结束；不把reference_complete=False等同门没有打开，也不称整活动全部完成。</p>'''
    page+='<p>实际VLA调用 '+str(audit['robot_actual_vla_calls'])+'；人NN '+str(audit['human_neural_calls'])+'。动作块来源：'+escape(json.dumps(counts,ensure_ascii=False))+'。</p>'
    page+='<video controls playsinline preload="none" src="'+os.path.relpath(root/'episode/demo.mp4',output)+'"><track kind="captions" srclang="zh-CN" label="研究注释" default src="'+os.path.relpath(caption,output)+'"></video><p>'
    page+=' · '.join('<a href="'+os.path.relpath(root/path,output)+'">'+label+'</a>' for path,label in links)
    page+='</p><p><a href="PROTOCOL.md">目的与预定设置</a> · <a href="conditions.csv">固定参考条件</a> · <a href="../area_feedback_20261009/index.html">动态三活动及原失败</a></p></section></main></html>'
    assert match['xml_equal'] and match['exact_saved_initial_state_match']
    assert process['drawer_opening_measurements']['opening_max_m']>.1
    assert summary['robot_native_goal_first_stable_s']==21.55
    (output/'index.html').write_text(page)
    print('发布40秒完整真实参考：开门成立，不计动态成绩')


if __name__=='__main__':build()
