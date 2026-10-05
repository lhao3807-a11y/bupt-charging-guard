"""下载公开车牌数据集（PLAN 任务 5.3 辅助）。

校园实拍尚未采集，先按「从公开数据集取真实照片」的方案备料：

- **CCPD2020（CCPD-Green）**：中国城市停车场实拍，**新能源绿牌** —— 对应本项目的
  「新能源」一类（绿牌 → vtype=新能源，契约 §3.1）。
- 蓝牌（燃油车）的 CCPD2019 官方包 12 GB 起、常见镜像 1.5–5 GB，本脚本**默认不下载**，
  需要时用 `--source ccpd2019-subset` 单独拉（见 SOURCES 表）。

用法::

    .venv-algo\\Scripts\\python.exe algo/tools/fetch_public_dataset.py
    .venv-algo\\Scripts\\python.exe algo/tools/fetch_public_dataset.py --source ccpd2019-subset

产物落在 ``algo/dataset_raw/``（已 gitignore），**不入库**。
本机需要走系统代理（注册表 HKCU ProxyServer），脚本会自动读取。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
ALGO = os.path.normpath(os.path.join(HERE, ".."))
RAW_DIR = os.path.join(ALGO, "dataset_raw")

SOURCES = {
    "ccpd2020-green": "https://huggingface.co/datasets/htkien95/ccpd2020/resolve/main/CCPD2020.zip",
    "ccpd2019-subset": "https://huggingface.co/datasets/zenitsu09/ccpd-subset-30k/resolve/main/ccpd_subset_30k.zip",
}


def system_proxy() -> dict[str, str] | None:
    """读 Windows 系统代理（HKCU\\...\\Internet Settings\\ProxyServer）。"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        value, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None
    if not value:
        return None
    url = value if "://" in value else f"http://{value}"
    return {"http": url, "https": url}


def download(name: str, url: str, proxies: dict[str, str] | None) -> str:
    import requests

    os.makedirs(RAW_DIR, exist_ok=True)
    dest = os.path.join(RAW_DIR, f"{name}.zip")
    if os.path.isfile(dest) and os.path.getsize(dest) > 1024 * 1024:
        print(f"已存在，跳过下载：{dest}（{os.path.getsize(dest) / 1048576:.1f} MB）")
        return dest

    print(f"下载 {name} → {dest}")
    started = time.time()
    with requests.get(url, proxies=proxies, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    pct = done / total * 100
                    print(f"\r  {done / 1048576:.1f}/{total / 1048576:.1f} MB ({pct:.1f}%)", end="")
        print()
    print(f"完成：{dest}（{os.path.getsize(dest) / 1048576:.1f} MB，用时 {time.time() - started:.0f}s）")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="下载公开车牌数据集")
    parser.add_argument(
        "--source",
        default="ccpd2020-green",
        choices=sorted(SOURCES),
        help="数据集源（默认绿牌 CCPD2020）",
    )
    args = parser.parse_args()

    try:
        import requests
    except ImportError:
        print("缺少 requests：.venv-algo\\Scripts\\python.exe -m pip install requests")
        return 1

    proxies = system_proxy()
    print(f"代理：{proxies}")
    try:
        download(args.source, SOURCES[args.source], proxies)
    except (requests.RequestException, OSError) as exc:
        # 网络/磁盘类失败统一给可操作的提示，不甩一整屏栈
        print(f"下载失败：{type(exc).__name__}: {exc}")
        print("若代理不通，可手动下载后放到 algo/dataset_raw/<name>.zip")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
