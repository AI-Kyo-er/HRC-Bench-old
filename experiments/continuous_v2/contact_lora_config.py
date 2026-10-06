"""原生 π0.5-DROID 的接触场景 LoRA 配置，保留官方数据变换与标度。"""
from dataclasses import replace

import flax.nnx as nnx
from openpi.models.pi0_config import Pi0Config
from openpi.shared.nnx_utils import PathRegex
from openpi.training.config import AssetsConfig, get_config
from openpi.training.optimizer import CosineDecaySchedule
from openpi.training.weight_loaders import CheckpointWeightLoader


def contact_lora_config(base_checkpoint, *, steps=400, batch_size=2):
    base = get_config("pi05_droid")
    model = Pi0Config(pi05=True, action_horizon=15,
                      paligemma_variant="gemma_2b_lora", action_expert_variant="gemma_300m_lora")
    data = replace(base.data, assets=AssetsConfig(assets_dir=str(base_checkpoint / "assets"), asset_id="droid"))
    return replace(base, name="pi05_droid_contact_lora", model=model, data=data,
                   freeze_filter=nnx.Not(PathRegex(".*lora.*")), ema_decay=None,
                   weight_loader=CheckpointWeightLoader(str(base_checkpoint / "params")),
                   num_train_steps=steps, batch_size=batch_size, fsdp_devices=1, wandb_enabled=False,
                   lr_schedule=CosineDecaySchedule(warmup_steps=20, peak_lr=5e-5,
                                                   decay_steps=max(steps, 21), decay_lr=1e-5))
