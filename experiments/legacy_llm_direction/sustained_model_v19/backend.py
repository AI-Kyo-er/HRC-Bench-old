"""固定官方thinking配置；一次生成，原最终JSON解析，不补采样。"""
import time
from experiments.reasoning_baseline_v17.adapter import PARAMETERS,MAX_NEW_TOKENS
from experiments.sustained_model_v19.inputs import parse_output

class Backend:
    def __init__(self,frozen):
        import torch
        from transformers import AutoTokenizer,Qwen3ForCausalLM
        self.torch=torch;self.frozen=frozen
        self.tokenizer=AutoTokenizer.from_pretrained(frozen['model_spec']['path'],local_files_only=True)
        self.model=Qwen3ForCausalLM.from_pretrained(frozen['model_spec']['path'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
        torch.cuda.reset_peak_memory_stats()
    def generate(self,messages,seed):
        torch=self.torch;tokenizer=self.tokenizer
        ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=True)
        assert len(ids)<=self.frozen['memory_estimate']['input_upper_bound_tokens'],('超过已冻输入预算，不截历史',len(ids))
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        inp=torch.tensor([ids],device='cuda:0',dtype=torch.long);start=time.monotonic()
        with torch.inference_mode():out=self.model.generate(input_ids=inp,attention_mask=torch.ones_like(inp),**PARAMETERS['thinking'],max_new_tokens=MAX_NEW_TOKENS,pad_token_id=tokenizer.eos_token_id)
        generated=out[0,len(ids):].tolist();response=tokenizer.decode(generated,skip_special_tokens=True)
        eos=self.model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
        return dict(messages=messages,seed=seed,input_ids=ids,generated_ids=generated,response=response,response_with_special_tokens=tokenizer.decode(generated,skip_special_tokens=False),
            input_tokens=len(ids),output_tokens=len(generated),generation_hit_limit=len(generated)==MAX_NEW_TOKENS and generated[-1] not in eos,seconds=time.monotonic()-start,
            think_end_marker_count=generated.count(151668),**parse_output(response))
    def metadata(self):
        t=self.torch
        return dict(model_id=self.frozen['model_spec']['model_id'],revision=self.frozen['model_spec']['revision'],model_path=self.frozen['model_spec']['path'],
            packages=self.frozen['packages'],parameters=PARAMETERS['thinking'],max_new_tokens=MAX_NEW_TOKENS,parameter_count=self.model.num_parameters(),dtype=str(self.model.dtype),
            attention='sdpa',quantization=None,offload=False,cuda=t.version.cuda,device=t.cuda.get_device_name(0),peak_allocated_bytes=t.cuda.max_memory_allocated(),peak_reserved_bytes=t.cuda.max_memory_reserved())
