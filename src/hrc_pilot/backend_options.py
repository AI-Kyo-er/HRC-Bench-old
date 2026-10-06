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
    parser.add_argument("--robot-grasp-model", choices=("kinematic_attachment", "friction_contact"),
                        default="kinematic_attachment",
                        help="friction_contact 使用自由碰撞刚体和实际夹爪摩擦，只接受底层关节动作")
    parser.add_argument("--experiment-tier", choices=("exploratory", "important"),
                        default="exploratory",
                        help="实验等级；important 要求 Genesis 真实 Sim 视频")
    parser.add_argument("--important", dest="experiment_tier", action="store_const",
                        const="important", help="重要实验快捷选项，等价于 --experiment-tier important")
    parser.add_argument("--assets-dir", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/assets/virtual-community"))
    parser.add_argument("--resolution", type=int, default=640)
    parser.add_argument("--render-stride", type=int, default=6)
    parser.add_argument("--video-settle-seconds", type=float, default=1.5,
                        help="任务成功或终止后继续录制真实 Sim 的秒数")
    parser.add_argument("--minimum-transfer-phase-seconds", type=float, default=0.20,
                        help="每个 Genesis 搬运阶段的最短物理时长")


def configure_backend(args, parser: argparse.ArgumentParser, output: Path):
    args._source_sha256 = {path.name: sha256(path.read_bytes()).hexdigest()
                          for path in Path(__file__).parent.glob("*.py")}
    if (args.resolution < 64 or not 1 <= args.render_stride <= 60
            or args.video_settle_seconds < 0
            or args.minimum_transfer_phase_seconds < 0):
        parser.error("resolution/render-stride/视频时长参数不合法")
    if getattr(args, "experiment_tier", "exploratory") == "important" and args.backend != "genesis":
        parser.error("important 实验必须使用 --backend genesis，才能保存真实 Sim 场景视频")
    if args.backend == "reference":
        if args.robot_grasp_model == "friction_contact":
            parser.error("friction_contact 要求 Genesis 后端")
        return ContinuousWorld
    gpu_rows = subprocess.check_output([
        "nvidia-smi", "--query-gpu=index,memory.free", "--format=csv,noheader,nounits"
    ], text=True)
    free = {row.split(",")[0].strip(): int(row.split(",")[1]) for row in gpu_rows.splitlines()}
    selected = os.environ.get("CUDA_VISIBLE_DEVICES") or max(free, key=free.get)
    required_memory = 4096
    if getattr(args, "partner_mode", None) == "qwen_llm":
        model_path = getattr(args, "human_model", None)
        weight_bytes = sum(path.stat().st_size for path in Path(model_path).glob("*.safetensors")) if model_path else 0
        required_memory = max(8192, int(weight_bytes / (1024 ** 2)) + 8192)
    if selected not in free or free[selected] < required_memory:
        parser.error(f"本次 Genesis 与伙伴模型预计需要 {required_memory} MiB 空闲显存，请指定足够空闲的单张 GPU")
    os.environ["CUDA_VISIBLE_DEVICES"] = selected
    data_root = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench")
    os.environ.setdefault("GS_CACHE_FILE_PATH", str(data_root / "cache/genesis-vico"))
    os.environ.setdefault("PYTHONPYCACHEPREFIX", str(data_root / "cache/pycache"))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("VICO_ASSET_PATHS", str(args.assets_dir))
    os.environ["VICO_PILOT_MINIMAL_IMPORTS"] = "1"
    from .continuous_genesis import make_genesis_backend_factory
    print(f"[continuous] GPU {selected}: {free[selected]} MiB 空闲，预计需要 {required_memory} MiB。", flush=True)
    return make_genesis_backend_factory(
        assets=args.assets_dir, output_root=output, resolution=args.resolution,
        render_stride=args.render_stride, policy=args.policy,
        settle_steps=round(args.video_settle_seconds * 60),
        minimum_transfer_phase_steps=round(args.minimum_transfer_phase_seconds * 60),
        robot_grasp_model=args.robot_grasp_model)


def backend_provenance(args) -> dict:
    tier = getattr(args, "experiment_tier", "exploratory")
    video_required = tier == "important" or args.backend == "genesis"
    current_hashes = {path.name: sha256(path.read_bytes()).hexdigest()
                      for path in Path(__file__).parent.glob("*.py")}
    captured_hashes = getattr(args, "_source_sha256", current_hashes)
    return {
        "backend": "GenesisContinuousAdapter" if args.backend == "genesis" else "ContinuousWorld",
        "experiment_tier": tier,
        "sim_video_required": video_required,
        "sim_video_contract": {
            "artifact": "demo.mp4",
            "per_episode": True,
            "runtime_recorded": True,
            "timeline_artifact": "video_timeline.json",
        },
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES") if args.backend == "genesis" else None,
        "grasp_model": args.robot_grasp_model if args.backend == "genesis" else "geometric_abstraction",
        "human_manipulation_model": "avatar_kinematic_attachment" if args.backend == "genesis" else "geometric_abstraction",
        "object_geometry": "free_rigid_box_50x50x100mm" if args.robot_grasp_model == "friction_contact" else "mug_mesh",
        "physics_hz": 60 if args.backend == "genesis" else None,
        "resolution": args.resolution,
        "render_stride": args.render_stride,
        "video_settle_seconds": args.video_settle_seconds,
        "minimum_transfer_phase_seconds": args.minimum_transfer_phase_seconds,
        "source_sha256": captured_hashes,
        "source_hash_capture": "before_backend_construction" if hasattr(args, "_source_sha256") else "report_time_filesystem",
        "source_files_changed_during_run": sorted(name for name in captured_hashes
                                                  if captured_hashes[name] != current_hashes.get(name)),
    }
