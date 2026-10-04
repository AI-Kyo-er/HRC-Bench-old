"""Benchmark 与 Dataset CLI 共用的后端选项和单卡运行配置。"""
from __future__ import annotations

import argparse
import os
import subprocess
from hashlib import sha256
from pathlib import Path

from .continuous import ContinuousWorld


def add_backend_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", choices=("reference", "genesis"), default="reference")
    parser.add_argument("--assets-dir", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/assets/virtual-community"))
    parser.add_argument("--resolution", type=int, default=640)
    parser.add_argument("--render-stride", type=int, default=6)


def configure_backend(args, parser: argparse.ArgumentParser, output: Path):
    if args.resolution < 64 or not 1 <= args.render_stride <= 60:
        parser.error("resolution 必须至少为 64；render-stride 必须在 1–60 之间")
    if args.backend == "reference":
        return ContinuousWorld
    gpu_rows = subprocess.check_output([
        "nvidia-smi", "--query-gpu=index,memory.free", "--format=csv,noheader,nounits"
    ], text=True)
    free = {row.split(",")[0].strip(): int(row.split(",")[1]) for row in gpu_rows.splitlines()}
    selected = os.environ.get("CUDA_VISIBLE_DEVICES") or max(free, key=free.get)
    if selected not in free or free[selected] < 4096:
        parser.error("Genesis 小场景预计需要 4 GB 空闲显存，请指定足够空闲的单张 GPU")
    os.environ["CUDA_VISIBLE_DEVICES"] = selected
    data_root = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench")
    os.environ.setdefault("GS_CACHE_FILE_PATH", str(data_root / "cache/genesis-vico"))
    os.environ.setdefault("PYTHONPYCACHEPREFIX", str(data_root / "cache/pycache"))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("VICO_ASSET_PATHS", str(args.assets_dir))
    os.environ["VICO_PILOT_MINIMAL_IMPORTS"] = "1"
    from .continuous_genesis import make_genesis_backend_factory
    print(f"[continuous] GPU {selected}: {free[selected]} MiB 空闲，预计需要 4 GB。", flush=True)
    return make_genesis_backend_factory(
        assets=args.assets_dir, output_root=output, resolution=args.resolution,
        render_stride=args.render_stride, policy=args.policy)


def backend_provenance(args) -> dict:
    return {
        "backend": "GenesisContinuousAdapter" if args.backend == "genesis" else "ContinuousWorld",
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES") if args.backend == "genesis" else None,
        "grasp_model": "kinematic_attachment" if args.backend == "genesis" else "geometric_abstraction",
        "physics_hz": 60 if args.backend == "genesis" else None,
        "resolution": args.resolution,
        "render_stride": args.render_stride,
        "source_sha256": {path.name: sha256(path.read_bytes()).hexdigest()
                          for path in Path(__file__).parent.glob("*.py")},
    }
