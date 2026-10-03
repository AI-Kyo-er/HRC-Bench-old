"""公开观察的唯一模型输入构造；不接收world、case评分或未来事件。"""
import copy
import hashlib
import json
from experiments.physical.protocol import parse
from experiments.reasoning_baseline_v17.adapter import final_answer
from experiments.sustained_activity_v18.protocol import SYSTEM,candidates,public_ledger

INSTRUCTIONS=[('request_transport','请求伙伴启动运输','left',0),('yield','等待伙伴完成当前运输','left',1),
    ('careful_red_left','将red绕行放入left','left',0),('place_blue_left','将blue放入left','left',3),
    ('place_blue_right','将blue放入right','right',3),('declare_done','宣布当前活动完成','left',4)]

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def public_aid(observation):
    ledger=public_ledger(observation['history']);binding=[]
    for e in observation['history']:
        if e['kind'] in ('update_proposed','proposal_reply'):
            binding.append({k:copy.deepcopy(e[k]) for k in ('kind','proposal_id','destination','decision') if k in e})
    done={i:goal in observation['physical_placements'][i] for i,goal in ledger['goals'].items()}
    return dict(source='仅从同一公开已发生history与当前实际physical_placements确定性归约；额外账本帮助，不提供下一动作。',
        current_goals_from_public_history=ledger['goals'],proposal_reply_binding=binding,pending_proposals=ledger['pending'],
        transport=dict(requested=any(e['kind']=='transport_request_reply' for e in observation['history']),rejected_count=ledger['rejections'],
            accepted_started=ledger['started'],delivery_occurred=observation['delivery_event'] is not None),
        done_under_current_goals=done,remaining_items=[i for i in ledger['goals'] if not done[i]],green_unassigned_preserve=True)

def messages(observation,view='full_history'):
    assert view in ('full_history','public_ledger_aid')
    obs=copy.deepcopy(observation)
    if view=='public_ledger_aid':obs['external_public_ledger_aid']=public_aid(obs)
    return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))]

def parse_output(response):
    final,boundary=final_answer(response,'thinking')
    if boundary:return dict(final_response=final,choice=None,parse_error=boundary)
    if not final:return dict(final_response=final,choice=None,parse_error='empty_final')
    choice,error=parse(final,candidates())
    return dict(final_response=final,choice=choice,parse_error=error)

def base_cases():
    return [dict(index=index,initial_blue=initial,update=update,availability=availability,seed=100)
        for index,(initial,update,availability) in enumerate((i,u,a) for i in ('left','right') for u in ('none','accepted','rejected') for a in ('ready','temporarily_busy'))]

def recognition_records(root):
    rows=[]
    for action,instruction,goal,sequence in INSTRUCTIONS:
        ident=f'Reference_{goal}_none_ready_public_ledger_parallel_100';path=root/'results/sustained_activity_v18/raw/reference'/ident/'decisions.json'
        source=json.loads(path.read_text())[sequence];observation=copy.deepcopy(source['observation'])
        for reverse in (False,True):
            o=copy.deepcopy(observation)
            if reverse:o['candidates'].reverse()
            o['explicit_next_instruction']=instruction
            index=len(rows);rows.append(dict(id=f'identify_{action}_{"reverse" if reverse else "normal"}',seed=1909000+index,
                source_case=ident,source_sequence=sequence,source_observation_sha256=digest(observation),source_messages_sha256=digest(source['messages']),
                observation=o,messages=messages(o),expected=action))
    return rows
