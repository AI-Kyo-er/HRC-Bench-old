"""旧锚点原评分；新交还公开ledger评分；所有选择均未物理执行。"""
import json
from experiments.physical.protocol import parse
from experiments.structure_diagnostic_v12.scoring import score as old_score
from experiments.structure_handoff_v15.new_scoring import score as new_score


def score_record(record,response):
    observation=json.loads(record['messages'][1]['content'])
    choice,error=parse(response,observation['candidates'])
    scorer=old_score if record['arm'] in ('old_anchor','manual_reminder') else new_score
    return dict(choice=choice,parse_error=error,score=scorer(choice,error,observation,record['reference_action']))
