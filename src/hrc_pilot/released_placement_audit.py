"""离线核对放置与显式持物归属；不选择动作或推断贡献归属。"""
from hashlib import sha256
import json
import math
from pathlib import Path

from .libero_native import perceived_object_contacts


def validate_target_definition(task,object_id,receiver_id):
    """绑定保存的公开目标，避免给别的物品套用该放置谓词。"""
    explicit=task.get('native_placement_goal')
    if explicit is not None:
        if explicit.get('kind') not in {'on','in'}:raise ValueError('目标不是放置关系')
        expected=(explicit['object_id'],explicit['receiver_id'])
    else:
        # 已保存旧格式的公开任务定义；未知任务须明确保存目标元数据。
        definitions={
            ('food_into_bowl','put the cream cheese in the bowl'):('cream_cheese_1','akita_black_bowl_1'),
            ('bottle_on_rack','put the wine bottle on the rack'):('wine_bottle_1','wine_rack_1'),
            ('bowl_on_stove','put the bowl on the stove'):('akita_black_bowl_1','flat_stove_1'),
        }
        key=(task['public_activity']['scene_case'],task['native_robot_task'])
        if key not in definitions:raise ValueError('缺少可核对的公开放置目标定义')
        expected=definitions[key]
    if (object_id,receiver_id)!=expected:raise ValueError('指定对象与保存的公开目标不一致')


def released_placement_records(trace, placements, object_id, receiver_id,
                               required_release_objects=None, stable_seconds=.2):
    """对保存的几何／支撑／速度证据再检查持物，不继承旧稳定计时。"""
    required=tuple(required_release_objects or (object_id,))
    if object_id not in required or len(set(required))!=len(required):
        raise ValueError('释放集合须含目标物品且无重复')
    if not math.isfinite(stable_seconds) or stable_seconds<=0:
        raise ValueError('稳定时间必须为有限正数')
    if len(trace)!=len(placements)+1 or not placements:
        raise ValueError('完整轨迹与逐步放置记录须对齐')
    duration=0.;records=[]
    for previous,current,placement in zip(trace,trace[1:],placements):
        dt=current['time_s']-previous['time_s']
        if not math.isfinite(dt) or dt<=0 or not math.isclose(
                current['time_s'],placement['time_s'],rel_tol=0.,abs_tol=1e-8):
            raise ValueError('放置与轨迹时间轴须严格递增并对应')
        if any(name not in current['objects'] for name in {*required,receiver_id}):
            raise ValueError('释放对象和支撑对象须存在于实际场景')
        actor=current['human_execution']
        # 没有载荷归属信息时，不能仅凭held_object为空宣布整个载荷释放。
        if 'carried_objects' not in actor or not isinstance(actor['carried_objects'],list):
            raise ValueError('缺少显式持物／载荷归属，不能认证释放')
        owned=set(actor['carried_objects'])
        if actor['held_object'] is not None:owned.add(actor['held_object'])
        contacts=perceived_object_contacts(current)
        human_owned=sorted(owned.intersection(required))
        hand_contacts=sorted(name for name in required if
            contacts[name]['robot_hand_contact'] or contacts[name]['human_hand_contact'])
        speed=placement['object_speed_m_s'];receiver_speed=placement['receiver_speed_m_s']
        if any(not math.isfinite(x) or x<0 for x in [speed,receiver_speed]):
            raise ValueError('放置速度须为有限非负数')
        released=bool(not human_owned and not hand_contacts and placement['released'])
        eligible=bool(placement['native_geometry_satisfied'] and placement['receiver_contact']
                      and released and speed<.08 and receiver_speed<.08)
        duration=duration+dt if eligible else 0.
        original=bool(placement['released_stable_placement'])
        corrected=duration>=stable_seconds-1e-9
        records.append({'time_s':current['time_s'],
            'original_record_success':original,'human_owned_required_objects':human_owned,
            'required_objects_with_actual_hand_contact':hand_contacts,
            'required_objects_released':released,'eligible_this_step':eligible,
            'recomputed_stable_duration_s':duration,'released_stable_placement':corrected})
    return records


def audit_run(root,object_id,receiver_id,required_release_objects=None,stable_seconds=.2):
    root=Path(root);names=['summary.json','provenance.json','episode/task.json','interaction_verification.json',
        'independent_video_verification.json','episode/trace.jsonl','episode/placement_evidence.jsonl']
    if (root/'failure.json').exists():raise ValueError('中断运行不能认证完整放置结果')
    sources={};data={}
    for name in names:
        raw=(root/name).read_bytes();sources[name]=sha256(raw).hexdigest()
        data[name]=([json.loads(line) for line in raw.decode().splitlines() if line.strip()]
                    if name.endswith('.jsonl') else json.loads(raw))
    for name in ['interaction_verification.json','independent_video_verification.json']:
        if data[name].get('status')!='verified':raise ValueError('要求完整输入／控制／视频核验')
    steps=data['provenance.json'].get('steps')
    if type(steps) is not int or len(data['episode/trace.jsonl'])!=steps+1:
        raise ValueError('缺少完整预定步数的终态轨迹')
    validate_target_definition(data['episode/task.json'],object_id,receiver_id)
    records=released_placement_records(data['episode/trace.jsonl'],data['episode/placement_evidence.jsonl'],
        object_id,receiver_id,required_release_objects,stable_seconds)
    conflicts=[r for r in records if r['original_record_success'] and not r['released_stable_placement']]
    return {'status':'source_bound_release_audit','object_id':object_id,'receiver_id':receiver_id,
        'required_release_objects':list(required_release_objects or (object_id,)),
        'stable_seconds':stable_seconds,'original_first_success_s':next(
            (r['time_s'] for r in records if r['original_record_success']),None),
        'released_first_success_s':next((r['time_s'] for r in records if r['released_stable_placement']),None),
        'terminal_released_stable_placement':records[-1]['released_stable_placement'],
        'conflicting_original_success_samples':len(conflicts),
        'human_owned_conflicting_samples':sum(bool(r['human_owned_required_objects']) for r in conflicts),
        'records':records,'source_sha256':sources,
        'analysis_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_files_changed_during_run':data['provenance.json'].get('source_files_changed_during_run'),
        'robot_contribution_score':None,'formal_benchmark_score':None,
        'scope':'指定放置关系的离线释放稳定核查；原始数据不改写，不证明完整活动、'
                '完整包含、有效约定、机器人贡献或cobalance，不进入策略输入。'}


def render_released_placement_audit(root):
    path=Path(root)/'released_placement_audit.json'
    if not path.exists():return ''
    saved=json.loads(path.read_text())
    current=audit_run(root,saved['object_id'],saved['receiver_id'],
        saved['required_release_objects'],saved['stable_seconds'])
    if current!=saved:raise ValueError('释放核查来源或分析已变化，须重新生成')
    return ('<h3>目标关系与真实释放分别核查</h3><p>原始放置记录首次成立：'
        +str(saved['original_first_success_s'])+'秒；结合显式持物／载荷、实际手部接触并重新累计稳定时间后：'
        +str(saved['released_first_success_s'])+'秒。此处只检查该放置关系，交付位置与双方约定另判。'
        '该结果不自动归为机器人贡献；原始摘要和轨迹保持保留。</p>')
