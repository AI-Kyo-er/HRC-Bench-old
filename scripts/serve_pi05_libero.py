#!/usr/bin/env python3
"""严格离线加载中国源仿真策略，在独立GPU上提供末端动作推理。"""
import argparse
from pathlib import Path

from openpi.serving.websocket_policy_server import WebsocketPolicyServer
from hrc_pilot.libero_torch_policy import LiberoTorchPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/lerobot/pi05-libero'))
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    policy=LiberoTorchPolicy(args.checkpoint)
    print('π0.5-LIBERO严格权重加载完成，末端动作7D',flush=True)
    WebsocketPolicyServer(policy,host='127.0.0.1',port=args.port,metadata=policy.metadata).serve_forever()


if __name__ == '__main__':
    main()
