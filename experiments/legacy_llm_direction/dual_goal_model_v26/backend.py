"""同一generate路径用于预算容量探针/正式思考；无自动修复或重抽。"""
import time
from experiments.reasoning_baseline_v17.adapter import PARAMETERS
from experiments.dual_goal_model_v26.inputs import parse_output

FLAGS=dict(logits_to_keep=1,return_dict_in_generate=False,output_scores=False,output_logits=False,output_attentions=False,output_hidden_states=False)


def generation_options(pad_token_id,capacity_only=False):
    options=dict(PARAMETERS['thinking'],**FLAGS,max_new_tokens=8192,pad_token_id=pad_token_id)
    if capacity_only:options['min_new_tokens']=8192
    return options


class Backend:
    def __init__(self,frozen):
        import torch
        from transformers import AutoTokenizer,Qwen3ForCausalLM
        self.torch=torch;self.frozen=frozen;self.tokenizer=AutoTokenizer.from_pretrained(frozen['model_spec']['path'],local_files_only=True)
        self.model=Qwen3ForCausalLM.from_pretrained(frozen['model_spec']['path'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
        torch.cuda.synchronize();self.loaded_memory=self.memory()

    def memory(self):
        t=self.torch;return dict(allocated_bytes=t.cuda.memory_allocated(),reserved_bytes=t.cuda.memory_reserved(),peak_allocated_bytes=t.cuda.max_memory_allocated(),peak_reserved_bytes=t.cuda.max_memory_reserved())

    def generate(self,messages,seed,capacity_only=False):
        torch=self.torch;t=self.tokenizer
        ids=t.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=True)
        if len(ids)>24576:raise ValueError(('input_capacity_failure:no_truncation',len(ids)))
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);inp=torch.tensor([ids],device='cuda:0',dtype=torch.long);start=time.monotonic()
        options=generation_options(t.eos_token_id,capacity_only)
        with torch.inference_mode():out=self.model.generate(input_ids=inp,attention_mask=torch.ones_like(inp),**options)
        torch.cuda.synchronize();generated=out[0,len(ids):].tolist();response=t.decode(generated,skip_special_tokens=True)
        eos=self.model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
        memory=self.memory();del out,inp
        r=dict(messages=messages,seed=seed,input_ids=ids,generated_ids=generated,response=response,response_with_special_tokens=t.decode(generated,skip_special_tokens=False),
            input_tokens=len(ids),output_tokens=len(generated),generation_hit_limit=len(generated)==8192 and generated[-1] not in eos,seconds=time.monotonic()-start,
            think_end_marker_count=generated.count(151668),memory=memory,capacity_only=capacity_only)
        if not capacity_only:r.update(parse_output(response))
        return r

    def metadata(self):
        t=self.torch
        return dict(model_id=self.frozen['model_spec']['model_id'],revision=self.frozen['model_spec']['revision'],model_path=self.frozen['model_spec']['path'],
            packages=self.frozen['packages'],parameters=PARAMETERS['thinking'],max_new_tokens=8192,dtype=str(self.model.dtype),attention='sdpa',generation_flags=FLAGS,
            quantization=None,offload=False,cuda=t.version.cuda,device=t.cuda.get_device_name(0),loaded_memory=self.loaded_memory,**self.memory())
