"""辅助下载四个尚未开始的官方分片；与原snapshot共享文件锁，不覆盖文件。"""
import concurrent.futures
import importlib.metadata
import json
import os
from pathlib import Path
import time

from huggingface_hub import HfApi, hf_hub_download

from experiments.physical.run import ROOT, save


def main():
    spec = json.loads((ROOT / 'results/model_scale_v4/model_spec.json').read_text())
    destination = Path('/data1/sieniwgroup/sieniw/HRC-Bench/models') / spec['model_id'].split('/')[-1]
    info = HfApi(token=False).model_info(spec['model_id'], revision=spec['revision'],
                                      files_metadata=True, token=False)
    files = sorted([f for f in info.siblings if f.rfilename.endswith('.safetensors')], key=lambda f: f.rfilename)
    selected = []
    cache = destination / '.cache/huggingface/download'
    for entry in files[-4:]:
        in_progress = list(cache.glob(f'*.{entry.lfs.sha256}.incomplete'))
        if (destination / entry.rfilename).exists() or in_progress:
            print('跳过已完成或有partial的分片', entry.rfilename, flush=True)
        else:
            selected.append(entry.rfilename)
    record = {'pid': os.getpid(), 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'revision': spec['revision'], 'files': selected, 'max_workers': 4,
               'local_dir': str(destination), 'force_download': False,
               'huggingface-hub': importlib.metadata.version('huggingface-hub'),
               'lock_safety': '相同local_dir、逐文件WeakFileLock，锁内已存在完整目标时跳过传输；原snapshot正常继续。'}
    save(ROOT / 'results/model_scale_v4/helper_receipt.json', record)
    print('辅助进程启动', json.dumps(record, ensure_ascii=False), flush=True)

    def fetch(name):
        print('开始未在写分片', name, flush=True)
        path = hf_hub_download(spec['model_id'], name, revision=spec['revision'],
                               local_dir=destination, token=False, force_download=False)
        print('分片完成', name, Path(path).stat().st_size, flush=True)
        return name

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        record['completed'] = list(pool.map(fetch, selected))
    record['exit_code'] = 0
    save(ROOT / 'results/model_scale_v4/helper_receipt.json', record)


if __name__ == '__main__':
    main()
