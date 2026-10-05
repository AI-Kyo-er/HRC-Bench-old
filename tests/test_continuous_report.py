"""检查回放使用历史证据而不重造实验。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hrc_pilot.continuous_report import build_replay_payload, write_continuous_report, rebuild_saved_report


class ContinuousReportTests(unittest.TestCase):
    def write_episode(self, root, mode="adaptive", offset=0.0):
        directory = root / mode / "example"
        directory.mkdir(parents=True)
        metrics = {"scenario": "example", "seed": 7, "partner_mode": mode,
                   "task_success": True, "steps": 2}
        scenario = {"name": "example", "description": "</script><script>bad()</script>",
                    "regions": {"tray": [0.5, 0.0, 0.8]}}
        trace = [{"step": index, "time_s": index / 10,
                  "objects": {"cup": [offset + index / 10, 0.0, 0.8]},
                  "human_position": [0.5, 0.8, 0.0],
                  "robot_position": [0.0, 0.0, 1.0],
                  "active_robot_action": "transfer:cup", "human_action": "observe"}
                 for index in range(2)]
        (directory / "metrics.json").write_text(json.dumps(metrics))
        (directory / "scenario.json").write_text(json.dumps(scenario))
        (directory / "trace.jsonl").write_text("\n".join(json.dumps(row) for row in trace))
        (directory / "events.jsonl").write_text(json.dumps({"kind": "robot_transfer_completed", "step": 1}))
        return metrics, directory, trace

    def test_historical_records_are_preserved_without_current_defaults(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, episode_dir, trace = self.write_episode(root)
            before = (episode_dir / "trace.jsonl").read_bytes()
            payload = build_replay_payload(root, [metrics])
            self.assertEqual(payload["episodes"][0]["trace"], trace)
            self.assertNotIn("activity", payload["episodes"][0]["scenario"])
            self.assertNotIn("robot_failures", payload["episodes"][0]["metrics"])
            write_continuous_report(root, [metrics])
            self.assertEqual((episode_dir / "trace.jsonl").read_bytes(), before)
            verification = json.loads((root / "replay_verification.json").read_text())
            self.assertFalse(verification["simulation_rerun"])
            self.assertEqual(verification["recorded_frame_count"], 2)
            self.assertEqual(verification["primary_visual_evidence"], "trajectory_canvas")

    def test_pair_comparison_checks_trajectory_not_only_frame_count(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first, _, _ = self.write_episode(root, "fixed_replay")
            second, _, _ = self.write_episode(root, "reactive")
            self.assertTrue(build_replay_payload(root, [first, second])["comparisons"][0]["trajectory_equal"])
            third, _, _ = self.write_episode(root, "adaptive", offset=0.02)
            self.assertFalse(build_replay_payload(root, [first, second, third])["comparisons"][0]["trajectory_equal"])

    def test_offline_document_escapes_data_and_keeps_original_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, _, _ = self.write_episode(root)
            (root / "index.html").write_text("original report")
            path = write_continuous_report(root, [metrics])
            document = path.read_text()
            self.assertNotIn("</script><script>bad()", document)
            self.assertNotIn("__REPORT_", document)
            self.assertIn('id="report-data"', document)
            self.assertIn('id="timeline"', document)
            self.assertEqual((root / "index.before-replay.html").read_text(), "original report")
            write_continuous_report(root, [metrics])
            self.assertEqual((root / "index.before-replay.html").read_text(), "original report")

    def test_missing_and_ambiguous_episode_sources_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, episode_dir, _ = self.write_episode(root)
            (episode_dir / "trace.jsonl").unlink()
            with self.assertRaisesRegex(ValueError, "缺少可回放轨迹"):
                build_replay_payload(root, [metrics])
            duplicate = root / "duplicate"
            duplicate.mkdir()
            (duplicate / "metrics.json").write_text(json.dumps(metrics))
            with self.assertRaisesRegex(ValueError, "无法唯一匹配"):
                build_replay_payload(root, [metrics])

    def test_counterfactual_rebuild_preserves_saved_video_alignment(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, episode_dir, _ = self.write_episode(root)
            timeline = {"fps": 10, "frames": [
                {"video_time_s": 0.0, "benchmark_time_s": None, "phase": "warmup"},
                {"video_time_s": 0.1, "benchmark_time_s": 0.0, "phase": "benchmark"},
            ]}
            (episode_dir / "video_timeline.json").write_text(json.dumps(timeline))
            (root / "history_counterfactual_summary.json").write_text(json.dumps({"episodes": [metrics]}))
            self.assertTrue(rebuild_saved_report(root).exists())
            payload = build_replay_payload(root, [metrics])
            self.assertEqual(payload["episodes"][0]["video_timeline"], timeline)
            self.assertIn("adaptive/example/video_timeline.json", payload["source_hashes"])

    def test_genesis_report_requires_nonempty_sim_video(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, _, _ = self.write_episode(root)
            (root / "provenance.json").write_text(json.dumps({"backend": "GenesisContinuousAdapter"}))
            with self.assertRaisesRegex(ValueError, "缺少有效真实 Sim 视频"):
                write_continuous_report(root, [metrics])

    def test_genesis_video_audit_is_written_to_payload_and_verification(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, episode_dir, _ = self.write_episode(root)
            (root / "provenance.json").write_text(json.dumps({"backend": "GenesisContinuousAdapter"}))
            (episode_dir / "demo.mp4").write_bytes(b"sim video")
            timeline = {"fps": 10, "frame_count": 2, "frames": [
                {"video_time_s": 0.0, "benchmark_time_s": 0.0},
                {"video_time_s": 0.1, "benchmark_time_s": 0.1},
            ]}
            (episode_dir / "video_timeline.json").write_text(json.dumps(timeline))
            write_continuous_report(root, [metrics])
            payload = build_replay_payload(root, [metrics])
            self.assertEqual(payload["video_summary"]["video_coverage"], 1.0)
            self.assertTrue(payload["episodes"][0]["video_audit"]["timeline_valid"])
            verification = json.loads((root / "replay_verification.json").read_text())
            self.assertTrue(verification["video_required"])
            self.assertEqual(verification["video_complete_count"], 1)
            self.assertEqual(verification["video_coverage"], 1.0)
            self.assertEqual(verification["primary_visual_evidence"], "runtime_recorded_sim_video")
            self.assertEqual(verification["rendering"], "runtime_sim_video_plus_recorded_xy_trajectory_canvas")

    def test_reference_backend_does_not_require_video(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, _, _ = self.write_episode(root)
            (root / "provenance.json").write_text(json.dumps({"backend": "ContinuousWorld"}))
            write_continuous_report(root, [metrics])
            verification = json.loads((root / "replay_verification.json").read_text())
            self.assertFalse(verification["video_required"])
            self.assertIsNone(verification["video_coverage"])


if __name__ == "__main__":
    unittest.main()
