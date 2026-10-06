"""独立核查 Genesis／原生MuJoCo 实验的运行时 Sim 视频及其时间轴。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import imageio.v2 as imageio
import numpy as np


ReaderFactory = Callable[[str], Any]


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and np.isfinite(value)


def verify_episode(directory: Path, root: Path, reader_factory: ReaderFactory = imageio.get_reader,
                   require_timeline: bool = False) -> dict[str, Any]:
    """核查单个 episode；reader_factory 允许单元测试注入无 GPU 解码器。"""
    directory = Path(directory)
    result: dict[str, Any] = {
        "episode": directory.relative_to(root).as_posix(),
        "status": "failed",
        "video": {"path": "demo.mp4", "exists": False, "bytes": 0, "decoded_frames": 0},
        "timeline": {"path": "video_timeline.json", "exists": False},
        "errors": [],
        "warnings": [],
    }
    video_path = directory / "demo.mp4"
    timeline_path = directory / "video_timeline.json"
    result["video"]["exists"] = video_path.is_file()
    result["video"]["bytes"] = video_path.stat().st_size if video_path.is_file() else 0
    if not video_path.is_file() or result["video"]["bytes"] <= 0:
        result["errors"].append("缺少非空 demo.mp4")
        return result
    reader = None
    try:
        reader = reader_factory(str(video_path))
        metadata = reader.get_meta_data() or {}
        fps = float(metadata.get("fps", 0))
        frame_count = 0
        shape = None
        for frame in reader:
            array = np.asarray(frame)
            if array.ndim < 2 or array.shape[0] <= 0 or array.shape[1] <= 0:
                raise ValueError("视频包含无效帧尺寸")
            shape = list(array.shape)
            frame_count += 1
        result["video"].update({"decoded_frames": frame_count, "fps": fps, "shape": shape})
        if frame_count <= 0:
            result["errors"].append("视频无法解码出帧")
        if not _finite_number(fps) or fps <= 0:
            result["errors"].append("视频 FPS 无效")
    except Exception as exc:  # 解码器会抛出多种后端特定异常
        result["errors"].append(f"视频解码失败：{exc}")
    finally:
        if reader is not None:
            reader.close()
    if not timeline_path.is_file():
        message = "缺少 video_timeline.json（视频仍可独立播放）"
        (result["errors"] if require_timeline else result["warnings"]).append(message)
        if not result["errors"]:
            result["status"] = "verified"
        return result
    result["timeline"]["exists"] = True
    try:
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        frames = timeline.get("frames")
        timeline_count = timeline.get("frame_count")
        timeline_fps = float(timeline.get("fps", 0))
        result["timeline"].update({"frame_count": timeline_count, "fps": timeline_fps})
        if not isinstance(frames, list) or not isinstance(timeline_count, int) or timeline_count <= 0:
            raise ValueError("frame_count 或 frames 不合法")
        if len(frames) != timeline_count:
            raise ValueError("frame_count 与 frames 长度不一致")
        if result["video"]["decoded_frames"] != timeline_count:
            raise ValueError("解码帧数与时间轴 frame_count 不一致")
        if not _finite_number(timeline_fps) or timeline_fps <= 0:
            raise ValueError("时间轴 FPS 无效")
        video_fps = result["video"].get("fps", 0)
        if abs(video_fps - timeline_fps) > max(0.05, timeline_fps * 0.01):
            raise ValueError("视频 FPS 与时间轴 FPS 不一致")
        video_times = [row.get("video_time_s") for row in frames]
        if not all(_finite_number(value) for value in video_times):
            raise ValueError("视频时间轴包含无效 video_time_s")
        if any(second <= first for first, second in zip(video_times, video_times[1:])):
            raise ValueError("video_time_s 必须严格递增")
        benchmark_times = [row.get("benchmark_time_s") for row in frames
                           if _finite_number(row.get("benchmark_time_s"))]
        trace_path = directory / "trace.jsonl"
        trace_times = []
        if trace_path.is_file():
            trace_times = [json.loads(line)["time_s"] for line in trace_path.read_text(encoding="utf-8").splitlines()
                           if line.strip()]
        if not benchmark_times:
            raise ValueError("时间轴没有 benchmark 帧")
        if any(second < first for first, second in zip(benchmark_times, benchmark_times[1:])):
            raise ValueError("benchmark_time_s 必须单调不减")
        if trace_times:
            tolerance = max(1 / 60, (trace_times[1] - trace_times[0]) if len(trace_times) > 1 else 1 / 10)
            if benchmark_times[0] > min(trace_times) + tolerance:
                raise ValueError("时间轴未覆盖 benchmark 起点")
            if benchmark_times[-1] < max(trace_times) - tolerance:
                raise ValueError("时间轴未覆盖 benchmark 终点")
        result["timeline"].update({"benchmark_frame_count": len(benchmark_times),
                                    "benchmark_start_s": benchmark_times[0],
                                    "benchmark_end_s": benchmark_times[-1]})
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result["errors"].append(f"时间轴核验失败：{exc}")
    if not result["errors"]:
        result["status"] = "verified"
    return result


def verify_result(root: Path, reader_factory: ReaderFactory = imageio.get_reader,
                  require_timeline: bool = False) -> dict[str, Any]:
    root = Path(root)
    episode_dirs = sorted({path.parent for path in root.rglob("metrics.json")})
    episodes = [verify_episode(directory, root, reader_factory, require_timeline) for directory in episode_dirs]
    failed = [episode for episode in episodes if episode["status"] != "verified"]
    return {
        "status": "verified" if episodes and not failed else "failed",
        "input_dir": str(root),
        "episode_count": len(episodes),
        "verified_episode_count": len(episodes) - len(failed),
        "failed_episode_count": len(failed),
        "warning_episode_count": sum(bool(episode["warnings"]) for episode in episodes),
        "timeline_required": require_timeline,
        "episodes": episodes,
        "interpretation": "真实运行视频、时间轴和保存轨迹的产物核查；不推断模型能力或 HRC 效果。",
    }


def finalize_video_verification(root: Path, *, required: bool,
                                require_timeline: bool = True) -> dict[str, Any] | None:
    """在正式报告前核验重要运行的视频契约。

    探索性参考后端不需要视频，因此直接返回 ``None``。重要运行必须为每个
    episode 解码出有效帧，并在默认设置下提供可与 benchmark 时间对齐的时间轴；
    核验结果始终写入运行根目录，失败时阻止后续报告生成。
    """
    if not required:
        return None
    root = Path(root)
    verification = verify_result(root, require_timeline=require_timeline)
    (root / "video_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    if verification["status"] != "verified":
        raise RuntimeError(f"重要实验真实 Sim 视频核验失败：{root / 'video_verification.json'}")
    return verification
