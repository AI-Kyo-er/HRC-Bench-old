"""Reproduce the small VC pilot environment on the project data disk."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench")
REPOSITORIES = {
    "Virtual-Community": ("https://github.com/UMass-Embodied-AGI/Virtual-Community.git",
                          "b1ace3b2d130746a52cac1ec0c1de05f4f90deec"),
    "Genesis-vico": ("https://github.com/UMass-Embodied-AGI/Genesis.git",
                     "cdbe596f23220b8134434dd0946039c4f493ab5a"),
}
ASSET_REVISION = "2325ce34be748231ab6d4197a2b525eef16cc10f"
ASSETS = {"avatars/models/mixamo_Alex_Jefferson.glb": 1298732,
          "avatars/motions/motion.pkl": 41067382}
ASSET_HASHES = {"avatars/models/mixamo_Alex_Jefferson.glb": "18e7a8e69c74227e79ca2a959fdffb85357e3431395145196f0cba938d1684ea",
               "avatars/motions/motion.pkl": "070f312b048afa6003a102eae04d5047a5b68499d31434c5baa0adcd8da4590c"}


def run(*args):
    print(" ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def link(target: Path, source: Path):
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        if source.resolve() != target.resolve():
            raise RuntimeError(f"已有链接指向其他位置：{source}")
    elif source.exists():
        raise RuntimeError(f"保留已有路径，不覆盖：{source}")
    else:
        source.symlink_to(target, target_is_directory=True)


def main():
    os.environ["UV_CACHE_DIR"] = str(DATA / "cache/uv")
    for folder in ("vendor", "envs", "cache/uv", "assets/virtual-community", "results/pilot_v1"):
        (DATA / folder).mkdir(parents=True, exist_ok=True)
    for name, (url, revision) in REPOSITORIES.items():
        checkout = DATA / "vendor" / name
        if not (checkout / ".git").exists():
            run("git", "init", checkout)
            run("git", "-C", checkout, "remote", "add", "origin", url)
            run("git", "-C", checkout, "fetch", "--depth", "1", "origin", revision)
            run("git", "-C", checkout, "checkout", "--detach", "FETCH_HEAD")
        actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        if actual != revision:
            raise RuntimeError(f"第三方版本不符：{name} {actual}，需要 {revision}")
        link(checkout, ROOT / "vendor" / name)
    patch = ROOT / "patches/vc-pilot-minimal-imports.patch"
    vc = DATA / "vendor/Virtual-Community"
    if "VICO_PILOT_MINIMAL_IMPORTS" not in (vc / "vico/modules/__init__.py").read_text():
        run("git", "-C", vc, "apply", patch)
    for filename, expected_size in ASSETS.items():
        path = DATA / "assets/virtual-community" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            url = f"https://huggingface.co/datasets/Virtual-Community-AI/assets/resolve/{ASSET_REVISION}/{filename}"
            print(f"下载 {filename}", flush=True)
            temporary = path.with_suffix(path.suffix + ".download")
            with urllib.request.urlopen(url, timeout=120) as source, temporary.open("wb") as dest:
                while block := source.read(1024 * 1024):
                    dest.write(block)
            temporary.replace(path)
        if path.stat().st_size != expected_size:
            raise RuntimeError(f"资产大小不符：{path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != ASSET_HASHES[filename]:
            raise RuntimeError(f"资产校验失败：{path}")
    link(DATA / "assets/virtual-community", DATA / "vendor/Virtual-Community/vico/assets/ViCo")
    environment = DATA / "envs/vc-pilot"
    if not (environment / "bin/python").exists():
        run("uv", "venv", "--python", "/usr/bin/python3.11", environment)
    python = environment / "bin/python"
    run("uv", "pip", "install", "--python", python, "torch==2.5.1", "torchvision==0.20.1",
        "--index-url", "https://download.pytorch.org/whl/cu121")
    run("uv", "pip", "install", "--python", python, "--no-deps", "-r", ROOT / "experiments/pilot_v1/requirements.lock.txt")
    run("uv", "pip", "install", "--python", python, "--no-deps", "-e", DATA / "vendor/Genesis-vico", "-e", ROOT)
    # VC's full lock includes city-generation and old model dependencies; use only its avatar components.
    run("uv", "pip", "install", "--python", python, "--no-deps", "-e", DATA / "vendor/Virtual-Community")
    link(environment, ROOT / ".venv-vc-pilot")
    link(DATA / "results/pilot_v1", ROOT / "results/pilot_v1")
    print("完成。运行 bash scripts/run_pilot_demo.sh", flush=True)


if __name__ == "__main__":
    main()
