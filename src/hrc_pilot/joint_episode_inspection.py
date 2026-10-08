"""供视频审阅的双方决策与实际状态；不回写模型输入，不生成协作评分。"""
from bisect import bisect_right
from copy import deepcopy
from hashlib import sha256
import json
from html import escape
import os
from pathlib import Path


def make_inspection(trace,human,plans,controls,timeline):
    actual={round(row['time_s'],6):i for i,row in enumerate(trace)}
    human_times=[row['time_s'] for row in human]
    robot_times=[row['time_s'] for row in plans]
    frames=[]
    for frame in timeline['frames']:
        time=frame.get('benchmark_time_s')
        if time is None:continue
        index=actual.get(round(time,6))
        if index is None:raise ValueError('视频帧没有对应实际轨迹')
        row=trace[index];execution=row['human_execution']
        # 最后状态没有后续控制；不能沿用最后动作伪称还在执行。
        control=controls[index] if index<len(controls) else None
        frames.append({'video_time_s':frame['video_time_s'],'benchmark_time_s':time,
            'trace_row':index,'human_decision_row':bisect_right(human_times,time)-1,
            'robot_decision_row':bisect_right(robot_times,time)-1,
            'human_execution':{k:deepcopy(execution[k]) for k in
                ['held_object','phase','motion_in_progress','active_motion_request_id',
                 'completed_requests','cancelled_requests','last_receipt'] if k in execution},
            'actual_robot_action_source':control['source'] if control else None,
            'measured_current_facts':deepcopy(row.get('observable_world',{}).get('current_measured_fact_sentences',[]))})
    if not frames:raise ValueError('没有可审阅的视频帧')
    return {'human_decisions':[{'benchmark_time_s':row['time_s'],'decision_id':row['decision_id'],
        'private_agenda':deepcopy(row.get('private_agenda_inference',{}).get('agenda_after')),
        'selected_contribution':deepcopy(row['choice']),'parse_error':row.get('parse_error')} for row in human],
        'robot_decisions':[{'benchmark_time_s':row['time_s'],
            'decision':deepcopy(row['decision']),'selected_skill_id':row.get('model_selected_skill_id'),
            'parse_error':row.get('parse_error')} for row in plans],
        'video_frames':frames,
        'scope':'独立研究审阅。私人需要只在报告显示，不进入机器人输入。选择、话语与实际执行分开；不自动判断完成、响应因果或cobalance。'}


def ensure_episode_inspection(root):
    root=Path(root);ep=root/'episode'
    for name in ['interaction_verification.json','independent_video_verification.json']:
        if json.loads((root/name).read_text()).get('status')!='verified':
            raise ValueError('完整输入／执行／视频核查后才生成研究视图')
    if not (root/'summary.json').is_file():raise ValueError('缺少完整终态')
    files={name:ep/name for name in ['trace.jsonl','human_policy_io.jsonl','robot_planner_io.jsonl',
                                    'robot_control.jsonl','video_timeline.json']}
    values={}
    hashes={}
    for name,path in files.items():
        raw=path.read_bytes();hashes['episode/'+name]=sha256(raw).hexdigest()
        values[name]=[json.loads(line) for line in raw.decode().splitlines() if line.strip()] if name.endswith('.jsonl') else json.loads(raw)
    result=make_inspection(values['trace.jsonl'],values['human_policy_io.jsonl'],
        values['robot_planner_io.jsonl'],values['robot_control.jsonl'],values['video_timeline.json'])
    result.update(source_sha256=hashes,generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    path=root/'episode_inspection.json'
    path.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    return path


def render_inspection_panel(root,output):
    path=ensure_episode_inspection(root)
    url=escape(os.path.relpath(path,output),quote=True)
    return ('<div class="episode-inspector" data-inspection="'+url+'">'
        '<p><strong>跟随视频核对双方行为</strong>：私人需要是人的解释，公开话语是表达，下面的执行状态来自当时实际环境。</p>'
        '<label>定位决策时刻 <select class="inspection-seek" disabled><option>正在加载</option></select></label>'
        '<p class="inspection-clock" data-view="clock">正在加载审阅记录</p>'
        '<div class="inspection-grid">'
        '<div><strong>人的私人需要</strong><p data-view="human-need"></p>'
        '<strong>人选择的当前贡献</strong><p data-view="human-choice"></p>'
        '<strong>人的公开话语</strong><p data-view="human-speech"></p></div>'
        '<div><strong>机器人选择与公开回应</strong><p data-view="robot-choice"></p>'
        '<p data-view="robot-speech"></p><strong>实际执行</strong><p data-view="execution"></p></div></div>'
        '<details><summary>当时的公开环境测量</summary><ul data-view="facts"></ul></details></div>')
