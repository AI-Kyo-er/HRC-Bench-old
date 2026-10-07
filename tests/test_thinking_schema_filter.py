import torch

from hrc_pilot.thinking_schema_filter import ThinkingSchemaFilter


def test_thought_tokens_remain_unconstrained_until_the_actual_end_marker():
    calls=[]
    def grammar(batch,sent):calls.append(sent.tolist());return [7,8]
    callback=ThinkingSchemaFilter(grammar,input_length=2,close_think_id=9,tool_prefix_ids=[4,5],vocab_size=12,eos_id=11)
    assert callback(0,torch.tensor([1,2,3]))==list(range(11)) and not calls
    assert callback(0,torch.tensor([1,2,3,9]))==[4]
    assert callback(0,torch.tensor([1,2,3,9,4]))==[5]
    assert callback(0,torch.tensor([1,2,3,9,4,5]))==[7,8]
    assert callback.json_start_index==6 and calls==[[1,2,3,9,4,5]]


def test_thinking_budget_only_closes_the_channel_and_does_not_pick_an_action():
    callback=ThinkingSchemaFilter(lambda *_:[7],input_length=2,close_think_id=9,
        tool_prefix_ids=[4],vocab_size=12,eos_id=11,thinking_limit=2)
    assert callback(0,torch.tensor([1,2,3,6]))==[9] and callback.forced_think_close
    assert callback(0,torch.tensor([1,2,3,6,9,4]))==[7]
