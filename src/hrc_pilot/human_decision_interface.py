"""人的当前贡献与公开交流分开编码；只执行模型明确选择的内容。"""
from copy import deepcopy
import json
import re

from .human_contribution_contract import parse_contribution
from .tool_joint_human import TOOL_NAME


CONTRIBUTIONS={'place_object':'relocate','hold_object':'pick','indicate_object':'point',
               'step_aside':'away','return_to_work':'return','wait':'wait'}
COMMUNICATIONS={'proposal','accept','reject','update','request','notice','finish'}


def decision_tool(scene):
    contribution={'type':'object','properties':{
        'kind':{'enum':list(CONTRIBUTIONS)},'object_id':{'enum':[None,*scene['objects_xyz']]},
        'destination':{'enum':[None,*available_destinations(scene)]}},'required':['kind'],'additionalProperties':False}
    communication={'type':'object','properties':{'kind':{'enum':sorted(COMMUNICATIONS)},
        'text':{'type':'string'}},'required':['kind','text'],'additionalProperties':False}
    return {'type':'function','function':{'name':TOOL_NAME,
        'description':'Choose your current contribution, communication and private intent independently. place_object reliably picks if necessary, moves and releases; no separate finger or pickup sequence is needed. Acceptance and finish are speech acts, never physical completion scores.',
        'parameters':{'type':'object','properties':{
            'contribution':{'anyOf':[{'type':'null'},contribution]},
            'communication':{'anyOf':[{'type':'null'},communication]},
            'intention':{'type':'string'},'participation':{'type':'string'},'reason':{'type':'string'},
            'memory':{'type':['string','null']}},'required':['contribution','communication'],'additionalProperties':False}}}


def available_destinations(scene):
    # 调试用初始中心不作为自然放置目标；不把名字相似的对象映射为目标。
    return {name:xyz for name,xyz in scene['regions_xyz'].items()
            if not name.endswith('_home') and name not in {'near_human','near_robot'}}


def decision_interface(scene):
    destinations=[]
    for name in available_destinations(scene):
        if name.endswith('_on_cabinet'):
            meaning='Actual cabinet top support surface, with placement height measured for '+name.removesuffix('_on_cabinet')+'.'
        elif name=='drawer_storage':meaning='Measured middle drawer interior support; accessibility is currently observed.'
        elif name.endswith('_personal'):meaning='Human-side table position for receiving or keeping this item.'
        else:meaning='Declared table position for preparing, receiving or delivering an item.'
        destinations.append({'destination_id':name,'meaning':meaning})
    return {'actor':'human','contributions':{
        'place_object':'Ensure selected object_id is placed and released at destination. Includes pickup when needed, or an already-satisfied receipt.',
        'hold_object':'Take and keep selected object_id; does not release it.',
        'indicate_object':'Indicate selected object_id; does not place it.',
        'step_aside':'Temporarily move away, possibly still holding an item.',
        'return_to_work':'Return to the work edge.',
        'wait':'Keep the currently selected motion or holding.'},
        'destination_choices':destinations,'object_ids':list(scene['objects_xyz']),
        'communication':'Accept, reject, request, update or finish with your actual words; does not mark the world or activity complete.',
        'one_current_contribution_not_plan_queue':True}


def parse_decision(raw,scene):
    calls=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',raw.rsplit('</think>',1)[-1],re.S)
    if len(calls)!=1:raise ValueError('需要一个完整的当前人决策调用')
    call=json.loads(calls[0]);args=call.get('arguments')
    if call.get('name')!=TOOL_NAME or not isinstance(args,dict):raise ValueError('非法人决策调用')
    if 'contribution' not in args or 'communication' not in args:raise ValueError('须分别声明贡献与交流，可明确为空')
    if set(args)-{'contribution','communication','intention','participation','reason','memory'}:raise ValueError('未知人决策字段')
    motion=args['contribution'];speech=args['communication'];value={k:v for k,v in args.items() if k not in {'contribution','communication'}}
    value.update(action='wait',message='',message_kind='notice')
    if motion is not None:
        if not isinstance(motion,dict) or set(motion)-{'kind','object_id','destination'}:raise ValueError('非法贡献字段')
        kind=motion.get('kind')
        if kind not in CONTRIBUTIONS:raise ValueError('未知人贡献')
        value.update(action=CONTRIBUTIONS[kind],object_id=motion.get('object_id'),destination=motion.get('destination'))
        if kind=='place_object':
            dest=motion.get('destination');obj=motion.get('object_id')
            if dest not in available_destinations(scene):raise ValueError('所选自然放置目标不存在')
            if dest.endswith('_on_cabinet') and dest.removesuffix('_on_cabinet')!=obj:
                raise ValueError('支持面放置高度不是为该物品测量的')
    if speech is not None:
        if not isinstance(speech,dict) or set(speech)-{'kind','text'} or speech.get('kind') not in COMMUNICATIONS or not isinstance(speech.get('text'),str):
            raise ValueError('非法公开交流')
        value.update(message=speech['text'],message_kind='notice' if speech['kind']=='finish' else speech['kind'])
    choice,normalization=parse_contribution(json.dumps(value,ensure_ascii=False),scene['objects_xyz'],available_destinations(scene),schema_version=5)
    normalization.update(communication_kind=speech['kind'] if speech else None,
        contribution_kind=motion['kind'] if motion else None,
        interpretation='只编码NN自己选择的贡献和原话；finish不等于实际完成，不生成下一贡献。')
    return choice,normalization,call
