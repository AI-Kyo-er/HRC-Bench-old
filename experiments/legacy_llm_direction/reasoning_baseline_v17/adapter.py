"""思考边界适配：绝不从reasoning搜索choice；最终答复沿用原parser。"""
from experiments.physical.protocol import parse

PARAMETERS={
    'thinking':dict(do_sample=True,temperature=.6,top_p=.95,top_k=20,min_p=0.0),
    'nonthinking':dict(do_sample=True,temperature=.7,top_p=.8,top_k=20,min_p=0.0),
}
MAX_NEW_TOKENS=8192


def final_answer(response,mode):
    assert mode in PARAMETERS
    if mode=='thinking':
        count=response.count('</think>')
        if count==0:return None,'missing_think_end'
        # 官方Qwen3使用最后的151668边界；完整raw和marker数另存用于审计。
        reasoning,final=response.rsplit('</think>',1)
        return final.strip(),None
    # 非thinking模板已在输入闭合空think，不要求输出再次闭合。
    if '<think>' in response or '</think>' in response:return None,'unexpected_thinking_in_nonthinking'
    return response.strip(),None


def score(record,response,mode):
    final,boundary_error=final_answer(response,mode)
    choice,error=(None,boundary_error) if boundary_error else parse(final,record['menu'])
    return dict(final_response=final,think_end_marker_count=response.count('</think>'),boundary_error=boundary_error,choice=choice,parse_error=error,acceptable=choice in record['allowed'])
