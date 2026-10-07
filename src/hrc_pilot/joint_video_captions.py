"""真实Sim视频的独立研究字幕；不修改视频、策略输入或任务判定。"""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import unicodedata


OBJECTS={'akita_black_bowl_1':'碗','cream_cheese_1':'奶酪','wine_bottle_1':'酒瓶',
         'plate_1':'餐盘','wooden_cabinet_1':'柜子','flat_stove_1':'炉面','wine_rack_1':'酒架'}
ACTIONS={'wait':'等候','relocate':'放置','pick':'持有','place':'放下','point':'指示',
         'away':'暂离','return':'返回','pause_current':'暂停自己的运动','move_hand':'移动手'}
PHASES={'idle':'静止','point':'指示','pick_approach':'接近物品','pick_lift':'取起物品',
        'transfer_raise':'抬高物品','transfer_translate':'搬运','transfer_lower':'放下物品',
        'transfer_retreat':'退手','return':'返回','away':'暂离'}
SKILLS={'cream_in_bowl':'奶酪入碗','bottle_on_rack':'酒瓶上架','open_middle_drawer':'打开中层抽屉',
        'bowl_on_stove':'碗放炉面','bottle_on_cabinet':'酒瓶放柜顶','bowl_inside_top_drawer':'碗放上层抽屉',
        'bowl_on_cabinet':'碗放柜顶','plate_front_stove':'移餐盘到炉前','bowl_on_plate':'碗放餐盘'}


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def plain(value):
    value=str(value or '').replace('\n',' ').replace('\r',' ')
    for name,label in OBJECTS.items():value=value.replace(name,label)
    return value


def destination(name):
    if not name:return ''
    table={'serving_ready':'准备区','snack_delivery':'交付区','drink_staging':'饮品准备区','drawer_storage':'抽屉内部'}
    if name in table:return table[name]
    if name.endswith('_personal'):return plain(name.removesuffix('_personal'))+'的个人桌面区'
    if name.endswith('_on_cabinet'):return '柜顶'
    return plain(name)


def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def wrap_line(value,width=48):
    lines=[];current='';cells=0
    for char in value:
        size=2 if unicodedata.east_asian_width(char) in {'W','F'} else 1
        if current and cells+size>width:
            lines.append(current);current='';cells=0
        current+=char;cells+=size
    if current:lines.append(current)
    return '\n'.join(lines)


def make_captions(trace,human,plans,contexts,timeline,controls):
    """用已保存时间轴绑定实际状态；选择不是动作完成，私人消息不提前显示。"""
    actual={round(row['time_s'],6):row for row in trace}
    frames=timeline['frames'];events=[];hi=ri=ci=-1
    for frame in frames:
        time=frame.get('benchmark_time_s')
        if time is None:continue
        row=actual.get(round(time,6))
        if row is None:raise ValueError('字幕帧没有对应实际轨迹状态')
        while hi+1<len(human) and human[hi+1]['time_s']<=time:hi+=1
        while ri+1<len(plans) and plans[ri+1]['time_s']<=time:ri+=1
        while ci+1<len(contexts) and contexts[ci+1]['time_s']<=time:ci+=1
        choice=human[hi]['choice'] if hi>=0 else {}
        selected=ACTIONS.get(choice.get('action'),plain(choice.get('action')) or '尚未选择')
        if choice.get('object_id'):selected+=' '+plain(choice['object_id'])
        if choice.get('destination'):selected+='→'+destination(choice['destination'])
        execution=row['human_execution']
        physical=PHASES.get(execution['phase'],plain(execution['phase']))
        physical+='／持有'+plain(execution['held_object']) if execution.get('held_object') else '／未持物'
        if ri>=0:
            plan=plans[ri];decision=plan['decision']
            robot=('保持／协商' if decision['mode']=='hold' else '移动末端' if decision['mode']=='move_ee' else
                   SKILLS.get(plan.get('model_selected_skill_id'),'执行模型操作'))
        else:
            index=min(max(0,round(time*20)),len(controls)-1)
            source=controls[index]['source'] if controls else ''
            robot='参考控制' if any(word in source for word in ['reference','replay']) else '模型控制'
        lines=[f'人选择：{selected}；实际：{physical}',f'机器人选择／控制：{robot}']
        if ci>=0:
            cue=contexts[ci];text=plain(cue['text'])
            if len(text)>52:text=text[:52]+'…'
            lines.append(f'给人的消息（{cue["time_s"]:.1f}秒）：{text}')
        content='\n'.join(escape(wrap_line(line),quote=False) for line in lines)
        video_time=frame['video_time_s']
        if not events or content!=events[-1]['text']:
            if events:events[-1]['end']=video_time
            events.append({'start':video_time,'end':video_time+1/timeline['fps'],'text':content})
        else:events[-1]['end']=video_time+1/timeline['fps']
    if not events:raise ValueError('没有可生成字幕的实际状态')
    return 'WEBVTT\n\n'+''.join(
        f'{stamp(e["start"])} --> {stamp(e["end"])} line:4% position:50% size:96% align:center\n{e["text"]}\n\n'
        for e in events)


def source_paths(root):
    return [p for p in [root/'provenance.json',*[root/'episode'/name for name in
        ['trace.jsonl','human_policy_io.jsonl','robot_planner_io.jsonl','private_context.jsonl',
         'robot_control.jsonl','video_timeline.json','demo.mp4']]] if p.exists()]


def captions_are_current(root):
    root=Path(root);path=root/'research_caption_provenance.json';caption=root/'episode/research_captions.vtt'
    if not path.exists() or not caption.exists():return False
    meta=json.loads(path.read_text())
    if meta.get('generator_sha256')!=sha256(Path(__file__).read_bytes()).hexdigest():return False
    if meta.get('caption_sha256')!=sha256(caption.read_bytes()).hexdigest():return False
    if set(meta.get('source_sha256',{}))!={p.relative_to(root).as_posix() for p in source_paths(root)}:return False
    return all((root/name).is_file() and sha256((root/name).read_bytes()).hexdigest()==digest
               for name,digest in meta.get('source_sha256',{}).items())


def ensure_research_captions(root):
    root=Path(root)
    if not (root/'summary.json').exists():raise ValueError('只为完整终态生成研究字幕')
    for name in ['interaction_verification.json','independent_video_verification.json']:
        if json.loads((root/name).read_text()).get('status')!='verified':raise ValueError('字幕需要已独立核验的运行')
    if captions_are_current(root):return root/'episode/research_captions.vtt'
    sources={p.relative_to(root).as_posix():sha256(p.read_bytes()).hexdigest() for p in source_paths(root)}
    ep=root/'episode'
    text=make_captions(rows(ep/'trace.jsonl'),rows(ep/'human_policy_io.jsonl'),rows(ep/'robot_planner_io.jsonl'),
        rows(ep/'private_context.jsonl'),json.loads((ep/'video_timeline.json').read_text()),rows(ep/'robot_control.jsonl'))
    assert sources=={p.relative_to(root).as_posix():sha256(p.read_bytes()).hexdigest() for p in source_paths(root)}
    caption=ep/'research_captions.vtt';caption.write_text(text)
    (root/'research_caption_provenance.json').write_text(json.dumps({
        'role':'posthoc_research_view_not_policy_observation','source_sha256':sources,
        'generator_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'caption_sha256':sha256(caption.read_bytes()).hexdigest(),
        'private_information_visibility':'researcher_only; robot received only actual public channels',
        'interpretation':'独立可关闭的字幕，展示选择、采样执行状态及实际收到的私人情境；不是完成评分，不改原视频或模型观测。'
    },ensure_ascii=False,indent=2))
    return caption
