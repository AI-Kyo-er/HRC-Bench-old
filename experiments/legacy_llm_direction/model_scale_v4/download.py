"""从官方Qwen仓库固定revision下载；不读取或发送HF认证凭据。"""
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[2]
DATA = Path('/data1/sieniwgroup/sieniw/HRC-Bench')


def main():
    spec = json.loads((ROOT / 'results/model_scale_v4/model_spec.json').read_text())
    repo, revision = spec['model_id'], spec['revision']
    if not repo.startswith('Qwen/') or len(revision) != 40:
        raise ValueError('只接受已核验的官方Qwen仓库与完整commit revision。')
    info = HfApi(token=False).model_info(repo, revision=revision, files_metadata=True, token=False)
    expected = {}
    for entry in info.siblings:
        if entry.rfilename.endswith('.safetensors'):
            expected[entry.rfilename] = {'bytes': entry.size, 'sha256': entry.lfs.sha256}
    destination = DATA / 'models' / repo.split('/')[-1]
    destination.mkdir(parents=True, exist_ok=True)
    link = ROOT / 'models' / destination.name
    if not link.exists():
        link.symlink_to(destination)
    print('开始官方固定版本下载', repo, revision, sum(x['bytes'] for x in expected.values()), flush=True)
    snapshot_download(repo, revision=revision, local_dir=destination, token=False,
        allow_patterns=['*.json', '*.safetensors', '*.txt', '*.md'], max_workers=2)
    import hashlib
    actual = {}
    for name, metadata in expected.items():
        path = destination / name
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        actual[name] = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
        if actual[name] != metadata:
            raise RuntimeError(f'官方权重大小/SHA校验失败：{name}')
        print('权重校验通过', name, actual[name]['bytes'], flush=True)
    receipt = {'model_id': repo, 'revision': revision, 'path': str(destination),
               'official_lfs_checksums': expected, 'local_weights': actual,
               'all_weights_match_official': actual == expected,
               'packages': {'huggingface-hub': __import__('importlib.metadata').metadata.version('huggingface-hub')}}
    (ROOT / 'results/model_scale_v4/download_receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print('下载及全部权重SHA验证完成', flush=True)


if __name__ == '__main__':
    main()
