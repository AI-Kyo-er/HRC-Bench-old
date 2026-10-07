"""显式理想感知的神经协调基线：共享冻结权重，私有上下文和记忆分离。"""
import json
import time

from .robot_coordination import validate_decision


PUBLIC_FIELDS={'time_s','robot_task','human_task','dialogue','state','history','current_goal','self_execution','observed_world'}
SYSTEM=(
    '你是共同活动中的机器人协调策略，self=robot，partner=human。输入中的observed_world是理想几何／接触感知，'
    '不是人的私有意图或评分。依据实际位置、抽屉开度、接触和公开交流决定当前贡献。'
    'history是你以前的想法，不能把它当现在的事实；self_execution只报告真正执行过的动作。'
    '你只有两种当前控制：execute把简短英文物品操作指令交给真实VLA；hold保持并允许表达等待／询问。'
    '取放／开关必须通过execute交给VLA，不可把移动末端或发送消息当成已经操作。'
    '人没有公开的需要你不知道；可以澄清、请求协助、提出安排，并接受对方公开提出的新用途或分工。'
    '不要为了继续原始目标而忽略新约定，也不要凭空宣布已经完成。考虑当前物品是否由人持有、是否有空间。'
    '你自己选择下一步，程序不根据得分或任务阶段选择动作。'
    '只输出完整JSON：mode（execute/hold）、instruction（execute用简短英文）、message（简短英文）、'
    'reason（一句话）、memory_note（一句话）、current_goal。不要输出长计划。')


class SymbolicRobotCoordinator:
    def __init__(self,human_provider,generator=None):
        self.provider=human_provider;self.generator=generator;self.decisions=[]
        self.metadata={'policy':'qwen3_symbolic_coordination_plus_vla','perception':'ideal_observable_geometry',
            'shared_frozen_model_weights_with_human':True,'shared_private_memory_with_human':False,
            'task_scores_available':False,'model':str(human_provider.model_path),
            'controls':['execute_vla','hold'],'interpretation':'独立策略系统，不等同裸VLA或纯视觉端到端能力。'}

    def infer(self,request):
        if set(request)!=PUBLIC_FIELDS:raise ValueError('协调策略只接受明确公开的字段')
        prompt=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        started=time.perf_counter()
        if self.generator:raw=self.generator(SYSTEM,prompt)
        else:
            import torch
            tokenizer=self.provider._tokenizer;model=self.provider._model
            encoded=tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
                tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors='pt').to(model.device)
            with torch.inference_mode():
                output=model.generate(input_ids=encoded,attention_mask=torch.ones_like(encoded),max_new_tokens=256,
                    do_sample=False,pad_token_id=tokenizer.eos_token_id)
            raw=tokenizer.decode(output[0,encoded.shape[-1]:],skip_special_tokens=True)
        decision,error=validate_decision(raw)
        if decision['mode']=='move_ee':
            decision={'mode':'hold','instruction':'','message':'','reason':'本策略没有直接末端运动工具。',
                      'memory_note':'','current_goal':'','plan':[]};error='unsupported_direct_motion'
        record={'public_input':request,'raw_output':raw,'decision':decision,'parse_error':error,
            'latency_s':time.perf_counter()-started,'system_prompt':SYSTEM,
            'neural_inferences':1,'source':'actual_qwen3_symbolic_coordinator'}
        self.decisions.append(record);return record
