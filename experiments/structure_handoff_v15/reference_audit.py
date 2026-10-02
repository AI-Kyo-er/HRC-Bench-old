"""冻结后规范容器比较与全tick独立审计；不改原passed或重跑物理。"""
import copy
import gzip
import json
from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import prefix_digest
from experiments.structure_v7.audit import regions
from experiments.structure_handoff_v15.reference_run import RESULT,FREEZE,hashes,old_id
from experiments.structure_handoff_v15.protocol import SYSTEM,candidates,reduce_history,CHILD_CONTENT


def normalize_containers(value):
    """只将tuple规范成list，字典键/字段/数值/接触一概保留，无容差。"""
    if isinstance(value,(tuple,list)):return [normalize_containers(v) for v in value]
    if isinstance(value,dict):return {k:normalize_containers(v) for k,v in value.items()}
    return value


def physical_equal(a,b):return normalize_containers(a)==normalize_containers(b)


def episode_audit(case):
    folder=RESULT/'raw/reference'/case['id'];s=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text())
    old_folder=ROOT/'results/structure_v11/raw/reference'/old_id(case);old=json.loads((old_folder/'summary.json').read_text());old_rows=json.loads((old_folder/'decisions.json').read_text())
    needed={r['before_tick'] for r in rows}|{s['handoff_audit']['before']['tick'],s['final_state']['tick']};snapshots={}
    with gzip.open(folder/'ticks.jsonl.gz','rt') as f:
        for line in f:
            state=json.loads(line)
            if state['tick'] in needed:snapshots[state['tick']]=state
    checks=[]
    for i,row in enumerate(rows):
        obs=row['observation'];snap=snapshots[row['before_tick']];old_index=i if i<3 else 4
        old_obs=copy.deepcopy(old_rows[old_index]['observation'])
        nohist=lambda o:{k:v for k,v in o.items() if k not in ('history','remaining_decisions')}
        h=obs['history'];new=rows[i+1]['observation']['history'] if i+1<len(rows) else h
        check=dict(decision=i+1,messages_exact=row['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            geometry_exact=physical_equal(obs['physical']['objects'],snap['objects']) and physical_equal(obs['physical']['partner_position'],snap['partner_position']),
            region_exact=obs['physical_placements']==regions(snap),candidates_exact=obs['candidates']==candidates(),only_public_keys=set(obs)=={'history','physical','physical_placements','remaining_decisions','candidates'},
            budget_actual=obs['remaining_decisions']==12-i,immutable_history_prefix=new[:len(h)]==h,
            feedback_once=i==len(rows)-1 or new[len(h):].count(dict(kind='action_feedback',choice=row['result']['choice'],content=row['result']['feedback']))==1,
            mechanical_observation_matches_old=nohist(obs)==nohist(old_obs),handoff_not_future_leaked=('partner_handoff' in [e['kind'] for e in h])==(i==3))
        checks.append(check)
    hand=s['handoff_audit'];checkpoint=s['checkpoint_observation'];public=reduce_history(checkpoint['history'])
    restored=dict(old_d5_physical_exact=physical_equal(hand['after'],old['finish_audit']['after']),final_physical_exact=physical_equal(s['final_state'],old['final_state']))
    raw_bad={k:v for k,v in s['checks'].items() if not v};assert set(raw_bad)==set(restored)
    current_checks=dict(s['checks']);current_checks.update(restored)
    contacts=contact_audit(folder/'ticks.jsonl.gz',s['body_ids']['robot'],s['body_ids']['partner'],s['body_ids']['objects'].values())
    prefix=prefix_digest(folder/'ticks.jsonl.gz',hand['after']['tick']);full=prefix_digest(folder/'ticks.jsonl.gz',s['final_state']['tick'])
    oldprefix=prefix_digest(old_folder/'ticks.jsonl.gz',old['finish_audit']['after']['tick']);oldfull=prefix_digest(old_folder/'ticks.jsonl.gz',old['final_state']['tick'])
    old_history=copy.deepcopy(old_rows[3]['observation']['history'])
    for e in old_history:
        if e['kind']=='accepted_child':e['content']=CHILD_CONTENT
    history_correct=checkpoint['history']==old_history+[hand['event']]
    extra=dict(contact_audit_exact=contacts==s['contacts'],all_zero_record=contacts['zero_record_passed'] and contacts['all_missing_distance_records']==0,
        handoff_state_matches_actual_tick=physical_equal(hand['before'],hand['after']) and physical_equal(hand['after'],snapshots[hand['after']['tick']]),
        partner_really_withdrawn=hand['after']['partner_position'][1]>.5 and not checkpoint['physical']['direct_path_blocked'],
        green_done_preserved=checkpoint['physical_placements']['green']==['right'] and s['green_done_while_child'],
        blue_real_neutral=checkpoint['physical_placements']['blue']==['neutral'],public_child_ended=not public['active'] and public['ended'],
        latest_outer_restored=public['goals']['blue']==public['outer']['blue'],history_only_documented_changes=history_correct,
        old_new_prefix_equal=prefix==oldprefix,old_new_full_trace_equal=full==oldfull,
        old_new_updates_same_tick=s['update_audit'][0]['before']['tick']==old['update_audit'][0]['before']['tick'],
        old_new_update_block_exact=s['update_audit'][0]['events']==old['update_audit'][0]['events'],
        handoff_no_target_fields=set(hand['event'])=={'kind','content'} and not any(w in hand['event']['content'] for w in ('left','right')))
    passed=s['success'] and all(current_checks.values()) and all(extra.values()) and all(all(v for k,v in c.items() if k!='decision') for c in checks)
    return dict(id=case['id'],passed=passed,original_run_passed=s['passed'],original_false_checks=raw_bad,normalized_restored_checks=restored,
        checks=checks,extra=extra,contacts=contacts,prefix_canonical_sha256=prefix,full_canonical_sha256=full,
        original_summary_sha256=sha(folder/'summary.json'),decisions_sha256=sha(folder/'decisions.json'),ticks_sha256=sha(folder/'ticks.jsonl.gz'))


def main():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['packages']==versions() and f['assets_sha256']==asset_hashes()
    episodes=[episode_audit(c) for c in f['cases']]
    report=dict(all_passed=all(e['passed'] for e in episodes),total=16,episodes=episodes,total_ticks=sum(e['contacts']['total_ticks'] for e in episodes),
        original_run_passed=0,original_run_exit_code=1,comparator_errata='冻结run对live接触tuple与旧JSON list做直接==，两state字段误false；保存JSON全字段及全tick规范轨迹完全匹配。此派生仅规范容器，无字段/精度/接触删减，不修改原passed/freeze/trace，也不重跑。',
        freeze_sha256=sha(FREEZE),postfreeze_audit_sha256=sha(ROOT/'experiments/structure_handoff_v15/reference_audit.py'),runtime_sources_unchanged=True)
    save(RESULT/'reference_audit.json',report);assert report['all_passed'];print('16新实际轨迹独立全tick/输入/旧物理匹配审计通过；原run exit1保留。',flush=True)


if __name__=='__main__':main()
