#!/usr/bin/env python3
"""单卡、离线、中国源OpenVLA-LIBERO原生动作服务。"""
import argparse
import os
from pathlib import Path
import subprocess

from hrc_pilot.openvla_native_policy import OpenVLANativePolicy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/zixiaoBios/openvla-7b-finetuned-libero-spatial'))
    parser.add_argument('--port',type=int,default=8770)
    args=parser.parse_args()
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True)
    free={row.split(',')[0].strip():int(row.split(',')[1]) for row in rows.splitlines()}
    selected=os.environ.get('CUDA_VISIBLE_DEVICES')
    required=sum(path.stat().st_size for path in args.checkpoint.glob('*.safetensors'))//(1024**2)+6144
    if selected not in free or free[selected]<required:parser.error(f'需要单卡至少{required}MiB空闲显存')
    from openpi.serving.websocket_policy_server import WebsocketPolicyServer
    policy=OpenVLANativePolicy(args.checkpoint)
    print('OpenVLA严格离线权重载入完成；单相机语言输入，原生7D动作',flush=True)
    WebsocketPolicyServer(policy,host='127.0.0.1',port=args.port,metadata=policy.metadata).serve_forever()


if __name__=='__main__':main()
