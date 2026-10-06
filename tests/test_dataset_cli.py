import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hrc_pilot.dataset_cli import finalize_dataset_run


class DatasetCliFinalizationTests(unittest.TestCase):
    def write_run(self, root: Path) -> None:
        episode = root / "test" / "example"
        episode.mkdir(parents=True)
        metrics = {
            "scenario": "example", "seed": 0, "partner_mode": "adaptive",
            "policy_name": "greedy_public", "history_condition": None,
            "task_success": True,
        }
        (episode / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
        (episode / "scenario.json").write_text(json.dumps({"name": "example"}), encoding="utf-8")
        (episode / "trace.jsonl").write_text(
            json.dumps({"time_s": 0.0}) + "\n" + json.dumps({"time_s": 0.1}),
            encoding="utf-8")
        (root / "summary.json").write_text(json.dumps({"episodes": [metrics]}), encoding="utf-8")

    def test_reference_run_writes_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_run(root)
            report, verification = finalize_dataset_run(
                root, "generate", "greedy_public",
                {"backend": "ContinuousWorld", "sim_video_required": False})
            self.assertTrue(report.exists())
            self.assertIsNone(verification)
            self.assertTrue((root / "provenance.json").exists())
            self.assertTrue((root / "replay_verification.json").exists())

    def test_required_video_is_verified_before_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_run(root)
            episode = root / "test" / "example"
            (episode / "demo.mp4").write_bytes(b"sim video")
            (episode / "video_timeline.json").write_text(json.dumps({
                "fps": 10, "frame_count": 2,
                "frames": [
                    {"video_time_s": 0.0, "benchmark_time_s": 0.0},
                    {"video_time_s": 0.1, "benchmark_time_s": 0.1},
                ],
            }), encoding="utf-8")
            with patch("hrc_pilot.dataset_cli.verify_result",
                       return_value={"status": "verified", "episode_count": 1}):
                report, verification = finalize_dataset_run(
                    root, "generate", "greedy_public",
                    {"backend": "GenesisContinuousAdapter", "sim_video_required": True})
            self.assertTrue(report.exists())
            self.assertEqual(verification, root / "video_verification.json")
            self.assertTrue(verification.exists())

    def test_required_video_failure_stops_report_generation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_run(root)
            with self.assertRaisesRegex(RuntimeError, "视频核验失败"):
                finalize_dataset_run(
                    root, "generate", "greedy_public",
                    {"backend": "GenesisContinuousAdapter", "sim_video_required": True})
            self.assertTrue((root / "video_verification.json").exists())
            self.assertFalse((root / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
