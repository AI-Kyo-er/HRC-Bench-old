#!/usr/bin/env python3
"""用实际接触示范适配 π0.5，仅训练 LoRA，使用官方 OpenPI 训练步骤。"""
import argparse
from dataclasses import asdict
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

from openpi.models.model import Observation
from openpi.shared import download
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
    def __init__(self, roots, split):
        self.datasets = [PhysicalFrameDataset(root, split=split, action_horizon=15) for root in roots]
        self.indices = [(dataset, index) for dataset in self.datasets for index in range(len(dataset))
                        if dataset[index]["action_valid"].all()]

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        dataset, cursor = self.indices[index]
        sample = dataset[cursor]
        sample.pop("action_valid")
        return sample


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
    args = parser.parse_args()
    if args.weights_dir.exists() or (args.output_dir.exists() and any(args.output_dir.iterdir())):
        parser.error("请使用新的模型权重与训练记录目录")
    args.output_dir.mkdir(parents=True)
    download.maybe_download = offline_download
    jax.config.update("jax_compilation_cache_dir", "/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/jax-contact-training")
    config = contact_lora_config(args.base_checkpoint, steps=args.steps, batch_size=args.batch_size)
    data_config = config.data.create(config.assets_dirs, config.model)
    raw_train, raw_dev = Frames(args.datasets, "train"), Frames(args.datasets, "dev")
    train = transform_dataset(raw_train, data_config)
    dev = transform_dataset(raw_dev, data_config)
    if not len(train) or not len(dev):
        parser.error("训练与验证都需要完整的15步真实动作块")
    train_cache, dev_cache = [train[i] for i in range(len(train))], [dev[i] for i in range(len(dev))]
    rng = np.random.default_rng(args.seed)

    def batch(cache, indices):
        stacked = jax.tree.map(lambda *values: np.stack(values), *[cache[index] for index in indices])
        return Observation.from_dict(stacked), stacked["actions"]

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
    print(f"[contact-lora] train={len(train)} dev={len(dev)}，仅 {trainable_count} 个 LoRA 参数训练", flush=True)
    step_fn = jax.jit(lambda state, batch: official.train_step(config, train_key, state, batch), donate_argnums=(0,))

    def eval_loss(params, batch, key):
        model = nnx.merge(state.model_def, params)
        model.eval()
        observation, actions = batch
        return jnp.mean(model.compute_loss(key, observation, actions, train=False))

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
                  "trainable_scope": "lora_only", "normalization": "original_droid_checkpoint_stats",
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
