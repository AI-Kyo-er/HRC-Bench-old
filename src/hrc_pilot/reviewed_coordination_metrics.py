"""对人工可读审阅所标的时间段计算过程量；不自动判定语义有效性。"""
from hashlib import sha256
import json
from html import escape
from pathlib import Path

from .joint_review_evidence import pointer_value


PUBLIC_TIME_FILES={'episode/public_dialogue.jsonl','episode/trace.jsonl',
                   'episode/human_policy_io.jsonl','episode/robot_planner_io.jsonl'}


def reviewed_metrics(root):
    root=Path(root).resolve()
    annotation_path=root/'coordination_process_review.json'
    annotation_bytes=annotation_path.read_bytes();review=json.loads(annotation_bytes)
    if review.get('review_type')!='assistant_review_of_saved_records_not_human_study':
        raise ValueError('必须明确标注审阅来源，不能伪装真人评分')
    if review.get('formal_benchmark_score') is not None:raise ValueError('本过程核查不能认证正式分数')
    for name in ['interaction_verification.json','independent_video_verification.json']:
        if json.loads((root/name).read_text()).get('status')!='verified':
            raise ValueError('过程评价要求完整输入／动作／视频核查')
    if not (root/'summary.json').exists():raise ValueError('缺少完整终态')
    sources={}
    def anchor_value(anchor):
        name=anchor['file'];path=(root/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root):raise ValueError('证据必须在本运行内')
        if name not in sources:
            raw=path.read_bytes()
            value=[json.loads(line) for line in raw.decode().splitlines() if line.strip()] if path.suffix=='.jsonl' else json.loads(raw)
            sources[name]={'sha256':sha256(raw).hexdigest(),'value':value}
        value=sources[name]['value']
        if 'row' in anchor:
            if path.suffix!='.jsonl' or type(anchor['row']) is not int or anchor['row']<0:
                raise ValueError('row必须是JSONL非空记录的零起始索引')
            value=value[anchor['row']]
        actual=pointer_value(value,anchor['pointer'])
        if json.dumps(actual,sort_keys=True,allow_nan=False)!=json.dumps(anchor['equals'],sort_keys=True,allow_nan=False):
            raise ValueError('审阅证据与保存记录不符')
        return actual
    trace_name='episode/trace.jsonl';control_name='episode/robot_control.jsonl'
    def load_rows(name):
        path=root/name;raw=path.read_bytes()
        value=[json.loads(line) for line in raw.decode().splitlines() if line.strip()]
        sources[name]={'sha256':sha256(raw).hexdigest(),'value':value}
        return value
    trace=load_rows(trace_name);controls=load_rows(control_name)
    dialogue=load_rows('episode/public_dialogue.jsonl')
    if len(trace)!=len(controls)+1:raise ValueError('过程量需要实际控制和状态对齐')
    if any(b['time_s']<=a['time_s'] for a,b in zip(trace,trace[1:])):raise ValueError('时间轴须严格递增')
    intervals=[]
    for item in review['reviewed_intervals']:
        if not item.get('interpretation') or not item.get('evidence'):raise ValueError('语义解释必须附原始证据')
        for key in ['start','end']:
            anchor=item[key]
            if anchor['file'] not in PUBLIC_TIME_FILES or anchor['pointer']!='/time_s':
                raise ValueError('只使用同一模拟时间轴，私人通知不能作为机器人公开响应的起点')
        if item['start']['file'] not in {'episode/public_dialogue.jsonl','episode/trace.jsonl'}:
            raise ValueError('起点须引用公开表达或实际环境，不能用私人推理替代公开线索')
        start=anchor_value(item['start']);end=anchor_value(item['end'])
        if isinstance(start,bool) or isinstance(end,bool) or not trace[0]['time_s']<=start<=end<=trace[-1]['time_s']:
            raise ValueError('审阅区间超出运行范围或起止时间无效')
        for evidence in item['evidence']:anchor_value(evidence)
        vla=hold=0.
        for index,control in enumerate(controls):
            duration=max(0.,min(end,trace[index+1]['time_s'])-max(start,trace[index]['time_s']))
            if control['source'] in {'actual_vla_coordinator_instruction','actual_vla_public_dialogue'}:vla+=duration
            if 'hold' in control['source']:hold+=duration
        human_messages=[message['text'] for message in dialogue
            if message['speaker']=='human' and start<=message['time_s']<end and message.get('text')]
        intervals.append({'label':item['label'],'reviewed_interpretation':item['interpretation'],
            'start_s':start,'end_s':end,'elapsed_sim_s':end-start,
            'actual_vla_control_s':vla,'selected_hold_control_s':hold,
            'human_public_message_count_in_interval':len(human_messages),
            'exact_repeated_human_message_count_in_interval':len(human_messages)-len(set(human_messages)),
            'semantic_status':'assistant_interpretation_not_independently_validated'})
    return {'status':'source_bound_measurements','review_sha256':sha256(annotation_bytes).hexdigest(),
        'source_sha256':{name:source['sha256'] for name,source in sources.items()},
        'analysis_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'reviewed_intervals':intervals,
        'formal_benchmark_score':None,
        'scope':'起止与执行时间可重建；有效响应、无谓劳动及负担含义来自明确标识的助手审阅。不给响应次数或时间赋协作总分，不把采样tick当独立样本。'}


def render_reviewed_metrics(root):
    root=Path(root)
    if not (root/'coordination_process_review.json').exists():return ''
    result=reviewed_metrics(root)
    saved=json.loads((root/'reviewed_coordination_metrics.json').read_text())
    if saved!=result:raise ValueError('过程量或源版本已变化，须重新执行独立过程评价')
    records=[]
    for interval in result['reviewed_intervals']:
        records.append('<tr><td>'+escape(interval['label'])+'</td><td>'+str(interval['start_s'])+' → '+str(interval['end_s'])+
            '</td><td>'+str(interval['elapsed_sim_s'])+'</td><td>'+str(interval['actual_vla_control_s'])+
            '</td><td>'+str(interval['exact_repeated_human_message_count_in_interval'])+'</td></tr>')
    interpretations=''.join('<p>'+escape(interval['reviewed_interpretation'])+'</p>' for interval in result['reviewed_intervals'])
    return ('<h3>有原始证据的过程量</h3><div class="scroll"><table><tr><th>审阅时间段</th><th>模拟秒</th>'
        '<th>间隔秒</th><th>实际VLA控制秒</th><th>人逐字重复说明次数</th></tr>'+''.join(records)+
        '</table></div>'+interpretations+'<p>数字依据实际记录；有效响应、过时劳动与负担的含义为助手解释，尚非独立专家评分。零延迟不代表成功；同轮区间没有长度，不用于统计该轮消息数量。</p>')
