"""Qwen3-VL仅文本单卡适配器；不调用视觉输入、不更改原messages。"""
from pathlib import Path
from experiments.model_scale_v4.backend import ConfigurableLocalModel


class LocalQwen3Text(ConfigurableLocalModel):
    def __init__(self,model_path,model_id,revision,max_new_tokens=96):
        import torch
        from transformers import AutoTokenizer,Qwen3VLForConditionalGeneration
        torch.manual_seed(0)
        self.model_path=str(Path(model_path).resolve());self.model_id=model_id;self.revision=revision;self.torch=torch
        self.tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
        self.model=Qwen3VLForConditionalGeneration.from_pretrained(model_path,local_files_only=True,
            dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
        self.max_new_tokens=max_new_tokens

    def metadata(self):
        result=super().metadata()
        result.update(model_class=type(self.model).__name__,input_modality='text_only',pixel_inputs=False,visual_capability_evaluated=False)
        return result
