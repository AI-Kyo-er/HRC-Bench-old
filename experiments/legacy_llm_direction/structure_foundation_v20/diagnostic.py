"""同几何两时机/两seed的原始接触定位；不产生新动作或改判。"""
import collections
import gzip
import json
from experiments.physical.run import ROOT,save,sha
from experiments.structure_foundation_v20.run_v1 import RESULT

def diagnostic():
    pairs=[]
    for seed in (120,121):
        timing_reports=[]
        for timing in ('during','after'):
            ident=f'B_right_{timing}_{seed}';folder=RESULT/'raw/BCD_dev1'/ident
            summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());row=next(r for r in rows if r['choice']=='green_right');ids=summary['body_ids']
            contacts={name:dict(records=0,first_record=None,first_negative_record=None,peak=None,phases={}) for name in ('green_carrier','robot_carrier','presence')}
            def evidence(s,c):return dict(tick=s['tick'],phase=s['phase'],ee=s['ee'],joint_positions=s['joint_positions'],carrier_joint=s['partner_joint'],carrier_position=s['partner_position'],carrier_velocity=s['partner_velocity'],
                green=s['objects']['green'],blue=s['objects']['blue'],presence=s['presence'],contact=c,commanded_placement=[.71,.25,.036])
            with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
                for line in stream:
                    state=json.loads(line)
                    if not (row['before_tick']<state['tick']<=row['after_tick']):continue
                    for c in state['contacts']:
                        pair={c['body_a'],c['body_b']};names=[]
                        if pair=={ids['objects']['green'],ids['carrier']}:names.append('green_carrier')
                        if pair=={ids['robot'],ids['carrier']}:names.append('robot_carrier')
                        if ids['presence'] in pair:names.append('presence')
                        for name in names:
                            group=contacts[name];group['records']+=1;group['phases'][state['phase']]=group['phases'].get(state['phase'],0)+1
                            e=evidence(state,c)
                            if group['first_record'] is None:group['first_record']=e
                            if group['first_negative_record'] is None and c['contact_distance']<-1e-6:group['first_negative_record']=e
                            if group['peak'] is None or c['normal_force']>group['peak']['contact']['normal_force']:group['peak']=e
            timing_reports.append(dict(id=ident,timing=timing,seed=seed,whole_script_passed=summary['passed'],first_green_skill_success=row['result']['success'],reason=row['result']['reason'],
                skill_before_tick=row['before_tick'],skill_after_tick=row['after_tick'],body_ids=ids,ee_servo_errors_m=row['result']['ee_errors'],
                phase_order=['approach','descend','lift','transit_detour_source','transit_detour_target','above_goal','place'],actual_green_after=row['after_state']['objects']['green'],
                contacts=contacts,decisions_sha256=sha(folder/'decisions.json'),trace_sha256=sha(folder/'ticks.jsonl.gz')))
        pairs.append(dict(seed=seed,conditions=timing_reports))
    report=dict(pairs=pairs,diagnostic_source_sha256=sha(ROOT/'experiments/structure_foundation_v20/diagnostic.py'),
        observation='仅运输中right提前放置两例失败、真实green/指爪与移动carrier接触；交付后同方向首技能无这些接触且成功；presence无接触。两时机共有transit约.0122m残差，不能把全部失败归于该共同误差。',
        limits='时间对照还改变carrier/blue位置与历史事件，不能仅凭对照宣称唯一因果或结构推理困难。公开状态等待、路径替代和red-first统一调度可能解决；未执行这些补充控制，不禁止简单正确策略。')
    save(RESULT/'timing_contact_diagnostic.json',report);print('原轨迹定位完成',[(p['seed'],[(r['timing'],r['first_green_skill_success']) for r in p['conditions']]) for p in pairs])

if __name__=='__main__':diagnostic()
