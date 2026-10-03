"""协议意图评分与blue尝试/方向分开；无新增物理执行。"""
from experiments.structure_diagnostic_v9.scoring import score as original_score
from experiments.structure_v7.protocol import reduce_history


def score(choice,error,observation,reference_action):
    result=original_score(choice,error,observation,reference_action)
    parts=(choice or '').split('_')
    attempted=error is None and len(parts)==3 and parts[0] in ('place','careful','assisted') and parts[1]=='blue'
    direction_correct=parts[2]==reduce_history(observation['history'])['goals']['blue'] if attempted else None
    result.update(blue_placement_attempted=attempted,blue_direction_correct=direction_correct,
        illegal_choice=not result['protocol_admissible'],
        duplicate_finish=error is None and choice=='finish_guidance' and not reduce_history(observation['history'])['active'])
    return result
