"""独立神经比较输入：保完整历史，仅澄清运输循环边界或添加公开账本。"""
import copy
import itertools
import json
from experiments.dual_goal_v25.protocol import Episode as ParentEpisode,SYSTEM,candidates,public_ledger,opposite
from experiments.dual_goal_v25.run import requirement
from experiments.physical.protocol import parse
from experiments.reasoning_baseline_v17.adapter import final_answer
from experiments.sustained_model_v19.inputs import digest

VIEWS=('full_history','public_ledger_aid')
ARMS=(('direct',VIEWS[0]),('direct',VIEWS[1]),('relation',VIEWS[0]),('relation',VIEWS[1]))
OLD_NOTE='right盘位于载台扫掠方向；green保持源处直到本控制循环结束。远端blue不能直接抓，需实际前送到近端。来源/职责不按私有目标筛。'
NEW_NOTE='right盘位于载台扫掠方向；运输循环指载台实际前送/返程，不是整个活动。载台沿y=0到0.60经过right盘，运输时已在right的物品可能被扫碰。载台已far稳定且无active时可整理green，并非必须等到活动结束。远端blue不能直接抓，需实际前送到近端。来源/职责不按私有目标筛。'


def clarify(observation):
    o=copy.deepcopy(observation);assert o['workspace']['notes'] in (OLD_NOTE,NEW_NOTE)
    o['workspace']['notes']=NEW_NOTE;return o


class Episode(ParentEpisode):
    def observation(self):return clarify(super().observation())


def public_aid(o):
    l=public_ledger(o['history']);done={i:g in o['physical_placements'][i] for i,g in l['goals'].items()}
    accepted=next(e for e in o['history'] if e['kind']=='accepted_activity')
    binding=[{k:copy.deepcopy(e[k]) for k in ('kind','proposal_id','binding','destination','decision') if k in e}
        for e in o['history'] if e['kind'] in ('proposal','proposal_reply')]
    return dict(source='仅从同一公开已发生history与当前实际physical_placements、motion归约；额外账本计算帮助，不提供未来、评分或下一动作。',
        current_goals_from_public_history=l['goals'],green_requirement=l['green_requirement'],proposal_reply_binding=binding,
        confirmation_pending=l['confirmation_pending'],pending_proposals=l['pending_proposals'],
        scope=dict(active=l['child_active'],check_completed=l['check_completed'],qualified_ticks_last_public=l['check_progress_observed']),
        done_under_current_goals=done,remaining_items=[i for i in l['goals'] if not done[i]],
        obligations=dict(inspection_required=accepted['inspection_required'],carrier_return_required=accepted['carrier_return_required'],
            current_carrier_far=o['physical']['carrier']['far'],motion_active=o['motion']['active']))


def messages(observation,view):
    assert view in VIEWS;o=clarify(observation)
    if view==VIEWS[1]:o['external_public_ledger_aid']=public_aid(o)
    return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(o,ensure_ascii=False))]


def parse_output(response):
    final,error=final_answer(response,'thinking')
    if error:return dict(final_response=final,choice=None,parse_error=error)
    if not final:return dict(final_response=final,choice=None,parse_error='empty_final')
    choice,error=parse(final,candidates());return dict(final_response=final,choice=choice,parse_error=error)


def records():
    result=[]
    for h,(blue,green) in enumerate(itertools.product(('left','right'),repeat=2)):
        rotation=h;arms=ARMS[rotation:]+ARMS[:rotation]
        for position,(expression,view) in enumerate(arms):
            q='same' if blue==green else 'opposite'
            case=dict(id=f'local_{blue}_{green}_{expression}',initial_blue=blue,reply='rejected',q=q,expression=expression,timing='before_check',direct_green=green,seed=120)
            result.append(dict(id=f'local_{h:02d}_{expression}_{view}',order=len(result),stage='local',group=h,position=position,case=case,view=view,seed_base=270000+100*h,decision_budget=12))
    for g,(initial,reply,q,timing) in enumerate(itertools.product(('left','right'),('accepted','rejected'),('same','opposite'),('before_check','after_handoff'))):
        rotation=g%4;arms=ARMS[rotation:]+ARMS[:rotation];final=opposite(initial) if reply=='accepted' else initial;green=final if q=='same' else opposite(final)
        for position,(expression,view) in enumerate(arms):
            case=dict(id=f'ref_{initial}_{reply}_{q}_{expression}_{timing}',initial_blue=initial,reply=reply,q=q,expression=expression,timing=timing,direct_green=green,seed=120)
            result.append(dict(id=f'full_{g:02d}_{expression}_{view}',order=len(result),stage='full',group=g,position=position,case=case,view=view,seed_base=260000+100*(g//2),decision_budget=48))
    assert len(result)==80 and len({r['id'] for r in result})==80;return result


def source_record(root,record):
    stage='local' if record['stage']=='local' else 'reference'
    path=root/'results/dual_goal_v25/raw/dev0'/stage/record['case']['id']/'decisions.json'
    rows=json.loads(path.read_text());index=next(i for i,r in enumerate(rows) if r['phase']=='local') if stage=='local' else 0
    o=clarify(rows[index]['observation'])
    return dict(source_path=str(path.relative_to(root)),source_sequence=index,source_observation_sha256=digest(rows[index]['observation']),
        initial_observation=o,initial_messages=messages(o,record['view']),prefix_cost=None if stage!='local' else json.loads(path.with_name('summary.json').read_text())['prefix_cost'])
