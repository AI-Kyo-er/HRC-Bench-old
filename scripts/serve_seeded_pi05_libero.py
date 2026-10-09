"""新episode使用独立种子的真实π服务；不热改已有服务或推断旧随机初态。"""
import argparse
from hashlib import sha256
from pathlib import Path

from openpi.serving.websocket_policy_server import WebsocketPolicyServer
from hrc_pilot.libero_torch_policy import LiberoTorchPolicy
from hrc_pilot.seeded_policy_inference import SeededPolicyInference


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--episode-seed', type=int, required=True)
    args = parser.parse_args()
    import os
    import subprocess
    entries = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free',
        '--format=csv,noheader,nounits'], text=True)
    free = {r.split(',')[0].strip(): int(r.split(',')[1]) for r in entries.splitlines()}
    selected = os.environ.get('CUDA_VISIBLE_DEVICES')
    required = (args.checkpoint / 'model.safetensors').stat().st_size // 1024**2 + 4096
    if selected not in free or free[selected] < required:
        parser.error(f'请先选择单卡至少{required}MiB空闲显存')
    policy = SeededPolicyInference(LiberoTorchPolicy(args.checkpoint), args.episode_seed)
    sources = [Path(__file__), Path('src/hrc_pilot/seeded_policy_inference.py'),
               Path('src/hrc_pilot/libero_torch_policy.py')]
    policy.metadata['sampler_source_sha256'] = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}
    print('独立episode种子的π0.5严格权重加载完成；禁止将本服务跨episode复用', flush=True)
    WebsocketPolicyServer(policy, host='127.0.0.1', port=args.port, metadata=policy.metadata).serve_forever()
