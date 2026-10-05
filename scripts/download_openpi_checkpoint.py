#!/usr/bin/env python3
"""下载官方 OpenPI 公共权重到共享模型目录，并核对对象 MD5。"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="pi05_droid")
    args = parser.parse_args()
    if not args.checkpoint or Path(args.checkpoint).name != args.checkpoint:
        parser.error("checkpoint 必须是单个目录名")
    prefix = f"checkpoints/{args.checkpoint}/"
    destination = Path("/data1/sieniwgroup/sieniw/models/Physical-Intelligence") / args.checkpoint
    destination.mkdir(parents=True, exist_ok=True)
    items = []
    token = None
    while True:
        query = {"prefix": prefix}
        if token:
            query["pageToken"] = token
        with urlopen("https://storage.googleapis.com/storage/v1/b/openpi-assets/o?" + urlencode(query), timeout=60) as response:
            page = json.load(response)
        items.extend(item for item in page.get("items", ()) if int(item.get("size", 0)) > 0)
        token = page.get("nextPageToken")
        if not token:
            break
    if not items:
        raise RuntimeError(f"官方公共桶没有找到 {prefix}")
    print(f"{len(items)} 个对象，共 {sum(int(item['size']) for item in items) / 1e9:.2f} GB → {destination}", flush=True)

    def fetch(item):
        relative = Path(item["name"].removeprefix(prefix))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"不合法对象路径：{relative}")
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.stat().st_size != int(item["size"]):
                raise RuntimeError(f"已有文件大小不同，保留原文件：{path}")
            digest = hashlib.md5()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
        else:
            partial = path.with_name(path.name + ".partial")
            digest = hashlib.md5()
            downloaded = partial.stat().st_size if partial.exists() else 0
            if downloaded:
                with partial.open("rb") as source:
                    for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
            if downloaded < int(item["size"]):
                headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}
                request = Request("https://storage.googleapis.com/openpi-assets/" + quote(item["name"], safe="/"), headers=headers)
                with urlopen(request, timeout=60) as response:
                    if downloaded and response.status != 206:
                        raise RuntimeError(f"服务端未按 Range 续传，保留部分文件：{partial}")
                    with partial.open("ab" if downloaded else "wb") as target:
                        for chunk in iter(lambda: response.read(8 * 1024 * 1024), b""):
                            target.write(chunk)
                            digest.update(chunk)
            if partial.stat().st_size != int(item["size"]):
                raise RuntimeError(f"下载大小不完整：{partial}")
            if base64.b64encode(digest.digest()).decode() != item["md5Hash"]:
                raise RuntimeError(f"下载校验不一致：{partial}")
            partial.replace(path)
        if base64.b64encode(digest.digest()).decode() != item["md5Hash"]:
            raise RuntimeError(f"模型文件校验不一致：{path}")
        print(f"已校验 {relative}", flush=True)
        return {key: item.get(key) for key in ("name", "size", "md5Hash", "generation")}

    with ThreadPoolExecutor(max_workers=4) as executor:
        verified = list(executor.map(fetch, items))
    (destination / "download_verification.json").write_text(json.dumps({
        "source": "gs://openpi-assets/" + prefix, "verified_objects": verified,
        "checkpoint": args.checkpoint, "checksum": "GCS MD5",
    }, ensure_ascii=False, indent=2))
    print(f"权重完整：{destination}", flush=True)


if __name__ == "__main__":
    main()
