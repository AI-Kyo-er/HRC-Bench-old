import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from scripts.verify_genesis_videos import verify_episode, verify_result
from hrc_pilot.video_verification import finalize_video_verification


class FakeReader:
    def __init__(self, frames, fps=10):
        self.frames = frames
        self.fps = fps

    def get_meta_data(self):
        return {"fps": self.fps}

    def __iter__(self):
        return iter(self.frames)

    def close(self):
        return None


def reader_factory(frames, fps=10):
    return lambda _path: FakeReader(frames, fps)


class GenesisVideoVerificationTests(unittest.TestCase):
    def write_episode(self, root, timeline=None, video_bytes=b"video"):
        episode = root / "adaptive" / "relay"
        episode.mkdir(parents=True)
        (episode / "metrics.json").write_text(json.dumps({"task_success": True}))
        (episode / "demo.mp4").write_bytes(video_bytes)
        trace = [{"time_s": 0.0}, {"time_s": 0.1}]
        (episode / "trace.jsonl").write_text("\n".join(json.dumps(row) for row in trace))
        if timeline is not None:
            (episode / "video_timeline.json").write_text(json.dumps(timeline))
        return episode

    def timeline(self, count=2):
        return {"fps": 10, "frame_count": count, "frames": [
            {"video_time_s": 0.0, "benchmark_time_s": 0.0},
            {"video_time_s": 0.1, "benchmark_time_s": 0.1},
        ][:count]}

    def test_missing_video_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            episode = self.write_episode(root, self.timeline())
            (episode / "demo.mp4").unlink()
            result = verify_episode(episode, root, reader_factory([np.zeros((2, 2, 3)), np.zeros((2, 2, 3))]))
            self.assertEqual(result["status"], "failed")
            self.assertIn("缺少非空 demo.mp4", result["errors"])

    def test_empty_video_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            episode = self.write_episode(root, self.timeline(), video_bytes=b"")
            result = verify_episode(episode, root, reader_factory([np.zeros((2, 2, 3)), np.zeros((2, 2, 3))]))
            self.assertEqual(result["status"], "failed")

    def test_frame_count_mismatch_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            episode = self.write_episode(root, self.timeline())
            result = verify_episode(episode, root, reader_factory([np.zeros((2, 2, 3))]))
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("帧数" in error for error in result["errors"]))

    def test_valid_video_and_timeline_pass(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_episode(root, self.timeline())
            result = verify_result(root, reader_factory([np.zeros((2, 2, 3)), np.zeros((2, 2, 3))]))
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["verified_episode_count"], 1)

    def test_missing_timeline_is_warning_by_default(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_episode(root)
            result = verify_result(root, reader_factory=reader_factory([
                np.zeros((2, 2, 3)), np.zeros((2, 2, 3))
            ]))
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["warning_episode_count"], 1)

    def test_missing_timeline_can_be_required(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_episode(root)
            result = verify_result(root, reader_factory=reader_factory([
                np.zeros((2, 2, 3)), np.zeros((2, 2, 3))
            ]), require_timeline=True)
            self.assertEqual(result["status"], "failed")

    def test_optional_finalization_does_not_read_or_write(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("hrc_pilot.video_verification.verify_result") as verify:
                self.assertIsNone(finalize_video_verification(root, required=False))
                verify.assert_not_called()
            self.assertFalse((root / "video_verification.json").exists())

    def test_finalization_records_verified_video(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_episode(root, self.timeline())
            verify = lambda root, **kwargs: verify_result(
                root, reader_factory([np.zeros((2, 2, 3))] * 2), **kwargs)
            with patch("hrc_pilot.video_verification.verify_result", side_effect=verify):
                result = finalize_video_verification(root, required=True)
            saved = json.loads((root / "video_verification.json").read_text())
            self.assertEqual(saved, result)
            self.assertEqual(saved["status"], "verified")
            self.assertTrue(saved["timeline_required"])

    def test_failed_finalization_stops_report_creation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_episode(root, self.timeline(), video_bytes=b"")
            with self.assertRaisesRegex(RuntimeError, "视频核验失败"):
                finalize_video_verification(root, required=True)
                (root / "index.html").write_text("正式报告")
            saved = json.loads((root / "video_verification.json").read_text())
            self.assertEqual(saved["status"], "failed")
            self.assertFalse((root / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
