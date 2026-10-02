"""纯可见观察模型适配器：predict接口只接受chat消息。"""
import importlib.metadata
import time


class LocalModel:
    def __init__(self, model_path, max_new_tokens=96):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.manual_seed(0)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True,
            torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa').eval()
        self.max_new_tokens = max_new_tokens

    def predict(self, messages):
        start = time.monotonic()
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=True, return_tensors='pt', return_dict=True).to('cuda:0')
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=self.max_new_tokens,
                pad_token_id=self.tokenizer.eos_token_id)
        tokens = output[0, inputs['input_ids'].shape[1]:]
        return {'response': self.tokenizer.decode(tokens, skip_special_tokens=True),
                'input_tokens': inputs['input_ids'].shape[1], 'output_tokens': len(tokens),
                'generation_hit_limit':len(tokens) == self.max_new_tokens and int(tokens[-1]) not in ([self.model.generation_config.eos_token_id] if isinstance(self.model.generation_config.eos_token_id,int) else self.model.generation_config.eos_token_id),
                'seconds': time.monotonic()-start}

    def metadata(self):
        return {'packages': {p: importlib.metadata.version(p) for p in
                            ('torch','transformers','huggingface-hub','accelerate')},
                'cuda': self.torch.version.cuda, 'gpu': self.torch.cuda.get_device_name(0),
                'visible_device': 3, 'seed':0, 'do_sample':False,
                'max_new_tokens':self.max_new_tokens,
                'peak_allocated_bytes':self.torch.cuda.max_memory_allocated()}
