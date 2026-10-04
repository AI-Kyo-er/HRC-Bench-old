#!/usr/bin/env python3
"""只读取已有结果，为参考仿真添加动画与实验说明。"""
import argparse
from pathlib import Path

from hrc_pilot.continuous_report import rebuild_saved_report


def main() -> None:
    parser = argparse.ArgumentParser(description="重建已有持续协作实验的离线动画报告")
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args()
    print(rebuild_saved_report(args.input_dir))


if __name__ == "__main__":
    main()
