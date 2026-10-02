"""复用冻结greedy/BF16实现，覆盖硬编码GPU元数据并明确模型身份。"""
import os
from pathlib import Path

from experiments.language.backend import LocalModel


class ConfigurableLocalModel(LocalModel):
    def __init__(self, model_path, model_id, revision, max_new_tokens=96):
        self.model_path = str(Path(model_path).resolve())
        self.model_id = model_id
        self.revision = revision
        super().__init__(model_path, max_new_tokens=max_new_tokens)

    def metadata(self):
        result = super().metadata()
        visible = os.environ.get('CUDA_VISIBLE_DEVICES')
        result['visible_device'] = int(visible) if visible and visible.isdigit() else visible
        result.update(model_id=self.model_id, revision=self.revision,
                      model_path=self.model_path, parameter_count=self.model.num_parameters(),
                      dtype=str(self.model.dtype), logical_device='cuda:0',
                      cuda_visible_devices=visible, attention_implementation='sdpa',
                      quantization=None, offload=False)
        return result
