"""事后接口校准：不改变正式评分、提示或模型，12个独立局部控制。"""
from pathlib import Path
import json
import hashlib
import time
from experiments.language.environment import Episode, DOMAINS, build_case, parse_action
from experiments.language.backend import LocalModel


def calibration_inputs():
    cases=[]
    for domain,d in DOMAINS.items():
        for profile in ('solo','assisted','yield','rejected_solo'):
            step={'solo':0,'assisted':1,'yield':2,'rejected_solo':1}[profile]
            item=d['items'][step]
            e=Episode(build_case(domain,'retain',0,'posthoc',False))
            e.step=step
            e.events=[{'kind':'propose','id':'control','item':item,
                       'destination':d['locations'][step%2],
                       'owner':'human' if profile=='yield' else 'robot'},
                      {'kind':'accept','id':'control'}]
            if profile in ('assisted','rejected_solo'):
                e.granted=profile=='assisted'
                e.events.append({'kind':'response','item':item,'accepted':e.granted})
            cases.append((domain,profile,e))
    return cases


def run():
    root=Path('results/language_v2/calibration')
    root.mkdir(parents=True,exist_ok=True)
    cases=calibration_inputs()
    inputs=[{'id':f'posthoc.{domain}.{profile}','messages':e.messages('oracle_summary')}
            for domain,profile,e in cases]
    (root/'inputs.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in inputs))
    receipt={'posthoc_interface_diagnostic':True,'created_unix_time':time.time(),
             'input_sha256':hashlib.sha256((root/'inputs.jsonl').read_bytes()).hexdigest(),
             'system_prompt_same_as_formal':True,'no_pending_corrections_or_composition':True}
    (root/'protocol.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    model=LocalModel('models/Qwen2.5-3B-Instruct')
    rows=[]
    with (root/'calls.jsonl').open('w') as f:
        for domain,profile,e in cases:
            pred=model.predict(e.messages('oracle_summary'))
            action,error=parse_action(pred['response'])
            row={'domain':domain,'profile':profile,'messages':e.messages('oracle_summary'),
                 **pred,'parse_error':error,'parsed_action':action,
                 'allowed_actions':e.allowed_actions(),
                 'action_valid':not error and action in e.allowed_actions(),
                 'completing_action':not error and action in e.allowed_actions() and action['action']!='request'}
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
            rows.append(row)
            print(domain,profile,pred['response'],row['action_valid'],flush=True)
    summary={'instances':12,'action_valid':sum(r['action_valid'] for r in rows),
             'completing_action':sum(r['completing_action'] for r in rows),
             'parse_errors':sum(r['parse_error'] is not None for r in rows),
             'generation_hit_limit':sum(r['generation_hit_limit'] for r in rows),
             'by_profile':{p:{'instances':3,'action_valid':sum(r['action_valid'] for r in rows if r['profile']==p),
                             'completing_action':sum(r['completing_action'] for r in rows if r['profile']==p)}
                           for p in ('solo','assisted','yield','rejected_solo')},'model':model.metadata()}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    run()
