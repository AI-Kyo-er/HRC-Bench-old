#!/usr/bin/env python3
"""直连中国ModelScope保存机器人策略；不使用环境代理或其他下载源。"""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
from urllib.parse import urljoin, urlparse

import requests


def allowed_host(url):
    host = urlparse(url).hostname or ''
    return (host == 'modelscope.cn' or host.endswith('.modelscope.cn')
            or (host.endswith('.aliyuncs.com') and '.oss-cn-' in host))


def china_response(session, url, **kwargs):
    for _ in range(8):
        if not allowed_host(url):
            raise ValueError('下载重定向离开中国ModelScope/中国区阿里云OSS，停止下载')
        response = session.get(url, allow_redirects=False, **kwargs)
        if response.is_redirect:
            url = urljoin(url, response.headers['Location'])
            response.close()
            kwargs.pop('params', None)
        else:
            response.raise_for_status()
            return response
    raise RuntimeError('ModelScope下载重定向次数过多')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='lerobot/pi05-libero')
    args = parser.parse_args()
    if len(Path(args.model).parts) != 2 or '..' in Path(args.model).parts:
        parser.error('模型ID必须为provider/name')
    root = Path('/data1/sieniwgroup/sieniw/models') / args.model
    root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.trust_env = False
    base = 'https://modelscope.cn/api/v1/models/' + args.model + '/repo'
    metadata = china_response(session, base + '/files', params={'Revision': 'master', 'Recursive': 'true'}, timeout=30).json()
    files = [item for item in metadata['Data']['Files'] if item['Type'] == 'blob']
    if shutil.disk_usage(root).free < sum(item['Size'] for item in files):
        raise RuntimeError('模型目录所在磁盘空闲空间不足')
    receipt = {'model': args.model, 'source': 'China_ModelScope', 'environment_proxies_used': False,
               'redirect_policy': 'modelscope.cn_or_oss-cn_aliyuncs.com_only', 'files': []}
    for item in files:
        relative = Path(item['Path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('模型文件路径不安全')
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + '.partial')
        offset = partial.stat().st_size if partial.exists() else 0
        if target.exists():
            digest = sha256(target.read_bytes()).hexdigest()
            if target.stat().st_size == item['Size'] and (not item.get('Sha256') or digest == item['Sha256']):
                receipt['files'].append({'path': str(relative), 'bytes': target.stat().st_size, 'sha256': digest})
                continue
        response = china_response(session, base, params={'Revision': item.get('Revision') or 'master', 'FilePath': str(relative)},
                                  headers={'Range': f'bytes={offset}-'} if offset else {}, stream=True, timeout=(15, 60))
        append = offset > 0 and response.status_code == 206
        if append and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
            raise RuntimeError('ModelScope断点响应与已有文件不一致')
        written = offset if append else 0
        milestone = written // (256 * 1024 * 1024)
        with partial.open('ab' if append else 'wb') as stream:
            for data in response.iter_content(chunk_size=4 * 1024 * 1024):
                stream.write(data)
                written += len(data)
                if written // (256 * 1024 * 1024) > milestone:
                    milestone = written // (256 * 1024 * 1024)
                    print(f'{relative}: {written}/{item["Size"]} bytes', flush=True)
        response.close()
        digest = sha256(partial.read_bytes()).hexdigest()
        if partial.stat().st_size != item['Size'] or (item.get('Sha256') and digest != item['Sha256']):
            raise ValueError(f'ModelScope文件大小或SHA256校验失败：{relative}')
        partial.replace(target)
        receipt['files'].append({'path': str(relative), 'bytes': written, 'sha256': digest})
    receipt.update(status='downloaded_and_verified', completed_at=datetime.now().astimezone().isoformat())
    (root / 'download_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(root, flush=True)


if __name__ == '__main__':
    main()
