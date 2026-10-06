#!/usr/bin/env python3
"""用实际接触示范适配 π0.5，仅训练 LoRA，使用官方 OpenPI 训练步骤。"""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import time
from urllib.parse import urlparse

import flax.nnx as nnx
import jax
import jax.numpy as jnp
import numpy as np
import optax

from openpi.models.model import Observation
from openpi.shared import download
from openpi.shared import normalize
from openpi.training import checkpoints, sharding
from openpi.training.data_loader import transform_dataset

from experiments.continuous_v2.contact_lora_config import contact_lora_config
from experiments.continuous_v2.physical_frame_dataset import PhysicalFrameDataset


def offline_download(url, **kwargs):
    """仅解析已有本地文件和缓存，禁止训练过程隐式下载任何权重。"""
    parsed = urlparse(str(url))
    path = (download.get_cache_dir() / parsed.netloc / parsed.path.strip("/")) if parsed.scheme else Path(url)
    if not path.exists():
        raise FileNotFoundError(f"离线训练缺少已有文件：{path}")
    return path.resolve()


class Frames:
    def __init__(self, roots, split, *, action_encoding="joint_velocity", complete_only=True):
        self.datasets = [PhysicalFrameDataset(root, split=split, action_horizon=15,
                                             action_encoding=action_encoding) for root in roots]
        self.indices = [(dataset, index) for dataset in self.datasets for index in range(len(dataset))
                        if not complete_only or dataset[index]["action_valid"].all()]

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        dataset, cursor = self.indices[index]
        sample = dataset[cursor]
        sample.pop("action_valid")
        return sample

    def mask(self, index):
        dataset, cursor = self.indices[index]
        return dataset[cursor]["action_valid"]


def position_norm_stats(dataset):
    """仅使用train；动作统计与实际DeltaActions变换一致，末尾无效时段不计入。"""
    states, targets = [], []
    for index in range(len(dataset)):
        sample = dataset[index]
        state = np.r_[sample["observation/joint_position"], sample["observation/gripper_position"]]
        relative = sample["actions"].copy()
        relative[:, :7] -= state[:7]
        states.append(state)
        targets.extend(relative[dataset.mask(index)])
    def stats(values):
        values = np.asarray(values)
        q01, q99 = np.quantile(values, [0.01, 0.99], axis=0)
        return normalize.NormStats(mean=values.mean(axis=0), std=values.std(axis=0),
                                   q01=q01, q99=np.maximum(q99, q01 + 0.001))
    return {"state": stats(states), "actions": stats(targets)}


def masked_position_train_step(config, rng, state, batch):
    """沿用官方NNX/Optax训练过程，仅将loss限定于真实记录的动作时段。"""
    model = nnx.merge(state.model_def, state.params)
    model.train()
    observation, actions, valid = batch
    def loss_fn(model):
        loss = model.compute_loss(jax.random.fold_in(rng, state.step), observation, actions, train=True)
        return jnp.sum(loss * valid) / jnp.maximum(jnp.sum(valid), 1)
    loss, grads = nnx.value_and_grad(loss_fn, argnums=nnx.DiffState(0, config.trainable_filter))(model)
    params = state.params.filter(config.trainable_filter)
    updates, opt_state = state.tx.update(grads, state.opt_state, params)
    nnx.update(model, optax.apply_updates(params, updates))
    return replace(state, step=state.step + 1, params=nnx.state(model), opt_state=opt_state), {
        "loss": loss, "grad_norm": optax.global_norm(grads),
    }


class LoaderAssets:
    def __init__(self, config):
        self.config = config

    def data_config(self):
        return self.config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", type=Path, required=True)
    parser.add_argument("--base-checkpoint", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/models/Physical-Intelligence/pi05_droid"))
    parser.add_argument("--weights-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20)
    parser.add_argument("--joint-position-expert", action="store_true",
                        help="训练完整动作专家及语言LoRA；使用实际控制位置目标和末尾时段mask")
    args = parser.parse_args()
    if args.weights_dir.exists() or (args.output_dir.exists() and any(args.output_dir.iterdir())):
        parser.error("请使用新的模型权重与训练记录目录")
    args.output_dir.mkdir(parents=True)
    download.maybe_download = offline_download
    jax.config.update("jax_compilation_cache_dir", "/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/jax-contact-training")
    encoding = "joint_position" if args.joint_position_expert else "joint_velocity"
    raw_train = Frames(args.datasets, "train", action_encoding=encoding, complete_only=not args.joint_position_expert)
    raw_dev = Frames(args.datasets, "dev", action_encoding=encoding, complete_only=not args.joint_position_expert)
    if args.joint_position_expert:
        from experiments.continuous_v2.contact_position_config import contact_position_config
        assets = args.output_dir / "assets"
        normalize.save(assets / "contact_position", position_norm_stats(raw_train))
        config = contact_position_config(args.base_checkpoint, assets, steps=args.steps, batch_size=args.batch_size)
    else:
        config = contact_lora_config(args.base_checkpoint, steps=args.steps, batch_size=args.batch_size)
    data_config = config.data.create(config.assets_dirs, config.model)
    train = transform_dataset(raw_train, data_config)
    dev = transform_dataset(raw_dev, data_config)
    if not len(train) or not len(dev):
        parser.error("训练与验证都需要完整的15步真实动作块")
    train_cache, dev_cache = [train[i] for i in range(len(train))], [dev[i] for i in range(len(dev))]
    if args.joint_position_expert:
        for cache, raw in ((train_cache, raw_train), (dev_cache, raw_dev)):
            for index, sample in enumerate(cache):
                sample["action_valid"] = raw.mask(index)
    rng = np.random.default_rng(args.seed)

    def batch(cache, indices):
        stacked = jax.tree.map(lambda *values: np.stack(values), *[cache[index] for index in indices])
        output = (Observation.from_dict(stacked), stacked["actions"])
        return (*output, stacked["action_valid"]) if args.joint_position_expert else output

    module_path = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/external/openpi/scripts/train.py")
    spec = importlib.util.spec_from_file_location("official_openpi_train", module_path)
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    mesh = sharding.make_mesh(1)
    train_key, init_key = jax.random.split(jax.random.key(args.seed))
    state, state_sharding = official.init_train_state(config, init_key, mesh, resume=False)
    jax.block_until_ready(state)
    trainable_count = sum(value.value.size for value in jax.tree.leaves(state.params.filter(config.trainable_filter),
                                                                      is_leaf=lambda item: isinstance(item, nnx.VariableState)))
    print(f"[contact-training] train={len(train)} dev={len(dev)}，{trainable_count} 个参数训练，编码={encoding}", flush=True)
    training_step = masked_position_train_step if args.joint_position_expert else official.train_step
    step_fn = jax.jit(lambda state, batch: training_step(config, train_key, state, batch), donate_argnums=(0,))

    def eval_loss(params, batch, key):
        model = nnx.merge(state.model_def, params)
        model.eval()
        observation, actions = batch[:2]
        loss = model.compute_loss(key, observation, actions, train=False)
        return (jnp.sum(loss * batch[2]) / jnp.maximum(jnp.sum(batch[2]), 1)
                if args.joint_position_expert else jnp.mean(loss))

    eval_fn = jax.jit(eval_loss)
    eval_indices = np.linspace(0, len(dev_cache) - 1, min(16, len(dev_cache)), dtype=int)
    eval_batches = [batch(dev_cache, eval_indices[i:i + args.batch_size])
                    for i in range(0, len(eval_indices), args.batch_size)]

    def evaluate():
        return float(np.mean([float(eval_fn(state.params, data, jax.random.fold_in(jax.random.key(2026), i)))
                              for i, data in enumerate(eval_batches)]))

    manager, _ = checkpoints.initialize_checkpoint_dir(args.weights_dir, keep_period=None, overwrite=False, resume=False)
    provenance = {"base_checkpoint": str(args.base_checkpoint), "model": asdict(config.model),
                  "seed": args.seed, "batch_size": args.batch_size, "steps": args.steps,
                  "train_samples": len(train), "dev_samples": len(dev), "trainable_parameters": trainable_count,
                  "trainable_scope": "full_action_expert_plus_language_lora_and_projections" if args.joint_position_expert else "lora_only",
                  "action_encoding": encoding,
                  "normalization": "train_only_relative_position_stats" if args.joint_position_expert else "original_droid_checkpoint_stats",
                  "partial_action_chunks": "masked_loss_on_real_steps" if args.joint_position_expert else "complete_windows_only",
                  "sampling": "仅使用完整动作块，dev保留最大示范seed；不声称跨任务或跨人泛化。",
                  "dataset_roots": [str(root) for root in args.datasets],
                  "dataset_metadata_sha256": {str(root): sha256((root / "dataset.json").read_bytes()).hexdigest()
                                               for root in args.datasets},
                  "official_training_step_sha256": sha256(module_path.read_bytes()).hexdigest(),
                  "interpretation": "操作域适配训练，训练或验证loss不代表仿真成功或HRC能力。"}
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    history = [{"step": 0, "dev_loss": evaluate()}]
    print(f"[contact-lora] step=0 dev_loss={history[-1]['dev_loss']:.6f}", flush=True)
    started = time.monotonic()
    with (args.output_dir / "training.jsonl").open("w", encoding="utf-8") as log:
        log.write(json.dumps(history[-1]) + "\n")
        for index in range(args.steps):
            data = batch(train_cache, rng.integers(len(train_cache), size=args.batch_size))
            with sharding.set_mesh(mesh):
                state, info = step_fn(state, data)
            info = jax.device_get(info)
            record = {"step": index + 1, "loss": float(info["loss"]), "grad_norm": float(info["grad_norm"]),
                      "elapsed_s": time.monotonic() - started}
            if (index + 1) % 50 == 0 or index == args.steps - 1:
                record["dev_loss"] = evaluate()
                print(f"[contact-lora] {record}", flush=True)
            history.append(record)
            log.write(json.dumps(record) + "\n")
            log.flush()
        checkpoints.save_state(manager, state, LoaderAssets(data_config), args.steps)
        manager.wait_until_finished()
    (args.output_dir / "summary.json").write_text(json.dumps({"status": "trained", "checkpoint": str(args.weights_dir / str(args.steps)),
        "initial_dev_loss": history[0]["dev_loss"], "final_dev_loss": history[-1]["dev_loss"],
        "steps": args.steps, "elapsed_s": time.monotonic() - started,
        "interpretation": "已完成真实权重更新，仍需独立闭环仿真评测。"}, ensure_ascii=False, indent=2))
    print(f"[contact-lora] checkpoint={args.weights_dir / str(args.steps)}", flush=True)


if __name__ == "__main__":
    main()
