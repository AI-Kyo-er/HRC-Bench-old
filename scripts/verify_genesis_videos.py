#!/usr/bin/env python3
"""独立核查 Genesis 实验的真实 Sim 视频及其时间轴。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hrc_pilot.video_verification import verify_episode, verify_result

__all__ = ["verify_episode", "verify_result"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True, help="Genesis 实验结果根目录")
    parser.add_argument("--require-timeline", action="store_true",
                        help="把逐帧 video_timeline.json 缺失或不一致视为失败")
    args = parser.parse_args()
    report = verify_result(args.input_dir, require_timeline=args.require_timeline)
    output = args.input_dir / "video_verification.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "verified":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
