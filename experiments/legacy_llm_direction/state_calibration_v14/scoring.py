"""原v13状态语义及原v12/v4动作评分，未执行动作不宣称物理成功。"""
import json
from experiments.state_readout_v13.semantic import parse_semantic
from experiments.state_readout_v13.scoring import score_state
from experiments.state_readout_v13.dataset import public_truth as history_truth
from experiments.state_calibration_v14.dataset import public_truth
from experiments.physical.protocol import parse
from experiments.structure_diagnostic_v12.scoring import score as action_score
from experiments.model_scale_v4.run import classify


def score_record(record,response):
    if record['query']=='state_readout':
        obs=json.loads(record['messages'][1]['content'])
        value,error,ordered=parse_semantic(response)
        truth=public_truth(obs) if record['suite']=='control' else history_truth(obs)
        score=score_state(value,error,truth)
        return dict(choice=None,state_value=value,parse_error=error,key_order_compliant=ordered,score=score)
    choice,error=parse(response,record['menu'])
    if record['suite']=='v13':score=action_score(choice,error,json.loads(record['messages'][1]['content']),record['reference_action'])
    else:
        original=dict(record,suite=record['original_suite'])
        score=dict(acceptable=choice in record['allowed'],errors=classify(original,choice,error),physical_execution=False,physical_success=None)
    return dict(choice=choice,state_value=None,parse_error=error,score=score)
