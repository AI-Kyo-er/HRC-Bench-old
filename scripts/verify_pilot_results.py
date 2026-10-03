"""Read-only integration verification of the completed pilot and its recorded evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from hrc_pilot.scenarios import SCENARIOS


def verify(result_dir: Path) -> dict:
    summary = json.loads((result_dir / "summary.json").read_text())
    assert summary["status"] == "complete", "运行尚未完整结束"
    assert len(summary["episodes"]) == summary["expected_episodes"]
    videos = []
    for metrics in summary["episodes"]:
        case, policy, seed = metrics["scenario"], metrics["policy"], metrics["seed"]
        episode = result_dir / f"{case}__{policy.replace(':', '_')}__seed{seed}"
        assert metrics["failed_skills"] == 0, f"底层技能失败污染合作对照：{episode.name}"
        trajectory = np.load(episode / "trajectory.npz", allow_pickle=False)
        length = len(trajectory["step"])
        assert length > 20 and np.all(np.diff(trajectory["step"]) >= 0)
        for key in trajectory.files:
            assert len(trajectory[key]) == length and np.isfinite(trajectory[key]).all(), (episode.name, key)
        assert trajectory["qpos"].shape[1] == 9
        assert np.max(np.ptp(trajectory["qpos"], axis=0)) > 0.05, "机械臂未发生实际关节运动"
        for i, object_id in enumerate(("red", "blue")):
            assert np.allclose(trajectory["objects"][-1, i], metrics["final_positions"][object_id], atol=1e-6)
        reader = imageio.get_reader(episode / "demo.mp4")
        metadata = reader.get_meta_data()
        frame_count = reader.count_frames()
        assert frame_count == length, f"视频与状态记录数量不符：{episode.name}"
        assert reader.get_data(0).shape == reader.get_data(frame_count - 1).shape
        reader.close()
        videos.append({"episode": episode.name, "frames": frame_count, "fps": metadata["fps"],
                       "duration_s": metadata["duration"]})
        io_rows = [json.loads(line) for line in (episode / "policy_io.jsonl").read_text().splitlines()]
        assert len(io_rows) == metrics["decisions"]
        for row in io_rows:
            obs = row["observation"]
            assert not ({"scenario", "expected_goal", "final_red", "human_available", "understanding", "rgb_path"} & obs.keys())
            assert obs["rgb"]["shape"] == [240, 320, 3]
        if policy in {"memory", "static", "reactive"}:
            expected = policy == "memory" or (
                policy == "static" and case not in {"information_update", "partner_unavailable"}
            ) or (policy == "reactive" and case != "history_keep")
            assert metrics["task_success"] == expected, f"机制对照不符合预期：{episode.name}"
        events = [json.loads(line) for line in (episode / "events.jsonl").read_text().splitlines()]
        if case == "information_update":
            update = next(e for e in events if e["kind"] == "partner_understanding_updated")
            assert update["physical_state_unchanged"]
            assert update["before_positions"] == update["after_positions"]
            assert update["previous"] == "pack" and update["current"] == "keep"
    pairs = []
    for pair in summary["history_pair_audits"]:
        assert pair["matched_within_tolerance"], "历史对照的物理状态不匹配"
        observations = []
        for case in ("history_keep", "history_pack"):
            folder = result_dir / f"{case}__{pair['policy'].replace(':', '_')}__seed{pair['seed']}"
            observations.append(hashlib.sha256((folder / "observation_01_03.png").read_bytes()).hexdigest())
        assert observations[0] == observations[1], "历史对照的首次机器人 RGB 不一致"
        pairs.append({"policy": pair["policy"], "seed": pair["seed"], "robot_rgb_identical": True})
    return {"status": "verified", "episode_count": len(videos), "videos": videos,
            "history_pairs": pairs, "all_manipulation_skills_succeeded": True,
            "scope": "手写机制对照与记录一致性；不是模型能力或统计显著性验证"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=Path("results/pilot_v1/formal"))
    args = parser.parse_args()
    report = verify(args.result_dir)
    (args.result_dir / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
