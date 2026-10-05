#!/usr/bin/env python3
"""在独立 OpenPI 环境加载官方 π0.5-DROID，通过本地 WebSocket 提供推理。"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from openpi.policies import policy_config
from openpi.serving.websocket_policy_server import WebsocketPolicyServer
from openpi.training.config import get_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/models/Physical-Intelligence/pi05_droid"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, force=True)
    policy = policy_config.create_trained_policy(get_config("pi05_droid"), args.checkpoint)
    print(f"模型已加载：{args.checkpoint}；本地端口 {args.port}", flush=True)
    WebsocketPolicyServer(policy, host="127.0.0.1", port=args.port,
                          metadata={**policy.metadata, "checkpoint": str(args.checkpoint),
                                    "config": "pi05_droid"}).serve_forever()


if __name__ == "__main__":
    main()
