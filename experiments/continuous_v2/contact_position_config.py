"""仿真关节位置域适配：训练完整动作专家、语言LoRA与动作投影。"""
from dataclasses import dataclass, replace

import flax.nnx as nnx
from openpi import transforms
from openpi.models.pi0_config import Pi0Config
from openpi.policies.droid_policy import DroidInputs, DroidOutputs
from openpi.shared.nnx_utils import PathRegex
from openpi.training.config import AssetsConfig, DataConfigFactory, ModelTransformFactory, get_config
from openpi.training.optimizer import CosineDecaySchedule
from openpi.training.weight_loaders import CheckpointWeightLoader


@dataclass(frozen=True)
class ContactPositionDataConfig(DataConfigFactory):
    def create(self, assets_dirs, model_config):
        mask = transforms.make_bool_mask(7, -1)
        data = transforms.Group(inputs=[DroidInputs(model_type=model_config.model_type)], outputs=[DroidOutputs()])
        data = data.push(inputs=[transforms.DeltaActions(mask)], outputs=[transforms.AbsoluteActions(mask)])
        return replace(self.create_base_config(assets_dirs, model_config), data_transforms=data,
                       model_transforms=ModelTransformFactory()(model_config))


def contact_position_config(base_checkpoint, assets_dir, *, steps=1200, batch_size=2):
    base = get_config("pi05_droid")
    model = Pi0Config(pi05=True, action_horizon=15, paligemma_variant="gemma_2b_lora",
                      action_expert_variant="gemma_300m")
    trainable = nnx.Any(PathRegex(".*llm.*_1.*"), PathRegex(".*lora.*"), PathRegex("(action_|time_).*"))
    data = ContactPositionDataConfig(assets=AssetsConfig(assets_dir=str(assets_dir), asset_id="contact_position"))
    return replace(base, name="pi05_contact_position", model=model, data=data,
                   freeze_filter=nnx.Not(trainable), ema_decay=None,
                   weight_loader=CheckpointWeightLoader(str(base_checkpoint / "params")),
                   num_train_steps=steps, batch_size=batch_size, fsdp_devices=1, wandb_enabled=False,
                   lr_schedule=CosineDecaySchedule(warmup_steps=50, peak_lr=5e-5,
                                                   decay_steps=max(steps, 51), decay_lr=1e-5))
