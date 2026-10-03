"""失败后一次授权恢复：分片5–8续传，不覆盖原辅助receipt或日志。"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import time

from huggingface_hub import HfApi, hf_hub_download
from experiments.physical.run import ROOT, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt-dir', type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.attempt_dir / 'helper_receipt.json'
    if receipt_path.exists():
        raise RuntimeError('恢复attempt receipt已存在，禁止覆盖。')
    spec = json.loads((ROOT / 'results/model_scale_v4/model_spec.json').read_text())
    destination = Path('/data1/sieniwgroup/sieniw/HRC-Bench/models') / spec['model_id'].split('/')[-1]
    info = HfApi(token=False).model_info(spec['model_id'], revision=spec['revision'],
                                      files_metadata=True, token=False)
    selected = sorted(f.rfilename for f in info.siblings if f.rfilename.endswith('.safetensors'))[-4:]
    record = {'pid': os.getpid(), 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'revision': spec['revision'], 'files': selected, 'max_workers': 4,
        'local_dir': str(destination), 'force_download': False,
        'resume_existing_partial': True, 'note': '原两worker恢复负责前段，辅助只5–8；同cache逐文件锁。未完成partial保留并通过HF Range续传。'}
    save(receipt_path, record)
    print('恢复辅助启动', json.dumps(record, ensure_ascii=False), flush=True)

    def fetch(name):
        path = hf_hub_download(spec['model_id'], name, revision=spec['revision'],
                               local_dir=destination, token=False, force_download=False)
        print('恢复分片完成', name, Path(path).stat().st_size, flush=True)
        return name

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        record['completed'] = list(pool.map(fetch, selected))
    record['exit_code'] = 0
    save(receipt_path, record)


if __name__ == '__main__':
    main()
