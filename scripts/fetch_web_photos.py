"""M1 网络实拍图采集：Wikimedia Commons + Openverse（均为可自由使用的真实照片）。

计划 §3.4 风险表备选②「网络公开数据集补充」的落地脚本。产出：
- algo/dataset_web_raw/meta_candidates.json  候选清单（含来源/许可/作者/URL）
- algo/dataset_web_raw/images/<id>.jpg       原始下载图（未筛选）

用法：
    python scripts/fetch_web_photos.py            # 全量采集
    python scripts/fetch_web_photos.py --probe    # 只拉清单不下载
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "algo", "dataset_web_raw")
IMG = os.path.join(OUT, "images")
PROXY = "http://127.0.0.1:7897"  # 本机固定代理，缺它出不去

UA = "bupt-charging-guard/1.0 (university course project; image collection for CV dataset)"

# ---------------------------------------------------------------------------
# 查询词：按四类场景的可视特征组织。
# 说明：检测器只标 plate 单类，四类场景是场景标签（充电中/已充满靠线缆与时间区分，
# 视觉上都是「车停在充电位」），所以采集目标是「中国车牌清晰可见的停车/充电实拍」，
# 场景标签在人工筛查阶段按画面内容打。
# ---------------------------------------------------------------------------
QUERIES = {
    "commons": [
        # 充电场景
        "充电桩",
        "充电站",
        "charging station China",
        "electric car charging China",
        "electric vehicle charging station China",
        "Tesla Supercharger China",
        "NIO Power Swap",
        "BYD charging station",
        # 新能源品牌（绿牌概率高）
        "BYD Qin",
        "BYD Song",
        "BYD Han",
        "BYD Seal",
        "BYD Dolphin",
        "BYD Yuan Plus",
        "Wuling Hongguang Mini",
        "Wuling Mini EV",
        "NIO car China",
        "NIO ES6",
        "NIO ET5",
        "XPeng",
        "Li Auto",
        "Li Xiang",
        "Aion car",
        "Aion S",
        "Zeekr",
        "Ora car",
        "Dongfeng Nammi",
        "Changan car China",
        "Geely Geometry",
        "Chery QQ",
        "Hongqi car",
        "Haval car",
        "MG4 China",
        "Tesla Model 3 China",
        "Tesla Model Y China",
        "Voyah",
        "Avatr",
        "Deepal",
        "Leapmotor",
        # 燃油车（蓝牌）
        "Volkswagen China car",
        "Volkswagen Sagitar",
        "Toyota Corolla China",
        "Honda CR-V China",
        "Buick Excelle",
        "Nissan Sylphy",
        "Volkswagen Lavida",
        "Toyota Camry China",
        "Honda Accord China",
        "Audi A4L",
        "BMW 5 Series China",
        "taxi China",
        # 停车场景
        "parking lot China",
        "car park China",
        "street parking China",
        "cars parked China",
        "parking Beijing",
        "parking Shanghai",
        "parking Shenzhen",
        "parking Guangzhou",
        "parking Chengdu",
    ],
    "openverse": [
        "charging station China",
        "charging pile",
        "EV charging parking",
        "electric car China",
        "BYD car",
        "Tesla China",
        "NIO car",
        "XPeng car",
        "Li Xiang car",
        "Wuling",
        "Aion",
        "Zeekr",
        "Chinese license plate",
        "car parking China",
        "street parking China",
        "Shenzhen car",
        "Beijing car street",
        "Guangzhou car",
        "Chengdu car",
        "plug-in hybrid China",
    ],
}

# Openverse 拒绝 ND（微调属于衍生使用）；NC 学术可用但记录在案。
OV_LICENSES = "by,by-sa,cc0,pdm,by-nc,by-nc-sa"


def _opener() -> urllib.request.OpenerDirector:
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    op.addheaders = [("User-Agent", UA)]
    return op


OP = _opener()


def _get(url: str, timeout: int = 40, retries: int = 4) -> bytes:
    last: Exception | None = None
    for i in range(retries):
        try:
            return OP.open(url, timeout=timeout).read()
        except Exception as exc:  # noqa: BLE001 网络抖动统一退避重试
            last = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET 失败 {url}: {last}")


def _jget(url: str) -> dict:
    return json.loads(_get(url))


def _dump_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def _extract(ext_meta: dict, key: str) -> str:
    v = ext_meta.get(key, {}).get("value", "")
    return v if isinstance(v, str) else ""


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


# ---------------------------------------------------------------------------
# Commons
# ---------------------------------------------------------------------------


def commons_search(query: str, limit: int = 30) -> list[dict]:
    """按关键词搜 Commons 文件页，带 imageinfo（缩略 URL + 许可元数据）。"""
    out: list[dict] = []
    for offset in (0, 30):
        if len(out) >= limit:
            break
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": 6,
            "srlimit": min(30, limit),
            "sroffset": offset,
        }
        d = _jget("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
        hits = d.get("query", {}).get("search", [])
        if not hits:
            break
        titles = [h["title"] for h in hits]
        d2 = _jget(
            "https://commons.wikimedia.org/w/api.php?"
            + urllib.parse.urlencode(
                {
                    "action": "query",
                    "format": "json",
                    "titles": "|".join(titles),
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    "iiurlwidth": 1600,
                }
            )
        )
        for page in d2.get("query", {}).get("pages", {}).values():
            ii = (page.get("imageinfo") or [{}])[0]
            ext_meta = ii.get("extmetadata") or {}
            if not ii.get("thumburl"):
                continue
            out.append(
                {
                    "source": "commons",
                    "title": page.get("title", ""),
                    "url": ii["thumburl"],
                    "page": ii.get("descriptionurl", ""),
                    "width": ii.get("width", 0),
                    "height": ii.get("height", 0),
                    "license": _extract(ext_meta, "LicenseShortName"),
                    "artist": _extract(ext_meta, "Artist"),
                    "query": query,
                }
            )
        time.sleep(0.6)
    return out


# ---------------------------------------------------------------------------
# Openverse
# ---------------------------------------------------------------------------


def openverse_search(query: str, pages: int = 2) -> list[dict]:
    out: list[dict] = []
    for page in range(1, pages + 1):
        params = {
            "q": query,
            "page_size": 20,
            "page": page,
            "license": OV_LICENSES,
            "extension": "jpg",
        }
        try:
            d = _jget("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params))
        except RuntimeError:
            break
        for r in d.get("results", []):
            url = r.get("url") or ""
            if not url:
                continue
            out.append(
                {
                    "source": "openverse",
                    "title": r.get("title") or "",
                    "url": url,
                    "page": r.get("foreign_landing_url") or "",
                    "width": r.get("width") or 0,
                    "height": r.get("height") or 0,
                    "license": f"{r.get('license', '')} {r.get('license_version', '')}".strip(),
                    "artist": r.get("creator") or "",
                    "query": query,
                }
            )
        time.sleep(0.8)
    return out


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="只拉清单不下载")
    ap.add_argument("--max-download", type=int, default=600)
    args = ap.parse_args()

    os.makedirs(IMG, exist_ok=True)
    list_path = os.path.join(OUT, "meta_candidates.json")

    cand: dict[str, dict] = {}
    for src, fn in (("commons", commons_search), ("openverse", openverse_search)):
        for q in QUERIES[src]:
            try:
                items = fn(q)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] {src}:{q} 失败 {exc}", flush=True)
                continue
            for it in items:
                key = it["url"].split("?")[0]
                if key in cand:
                    continue
                it["artist"] = _strip_html(it["artist"])[:200]
                cand[key] = it
            print(f"[collect] {src}:{q} +{len(items)} 累计 {len(cand)}", flush=True)

    # 过滤：ND 许可（微调属衍生使用）与太小图
    keep = {}
    for k, it in cand.items():
        lic = it["license"].lower()
        if "nd" in lic.split() or lic.startswith(("by-nd", "cc-by-nd")):
            continue
        if it["width"] and it["height"] and min(it["width"], it["height"]) < 500:
            continue
        keep[k] = it
    print(f"候选 {len(cand)} -> 许可/尺寸过滤后 {len(keep)}", flush=True)

    _dump_json(list_path, list(keep.values()))
    if args.probe:
        print("仅拉清单 ->", list_path)
        return 0

    done, failed = 0, 0
    for i, (k, it) in enumerate(list(keep.items())[: args.max_download]):
        ext = ".png" if k.lower().endswith(".png") else ".jpg"
        path = os.path.join(IMG, f"{i:04d}{ext}")
        if os.path.exists(path):
            done += 1
            continue
        try:
            data = _get(it["url"], timeout=60)
            if len(data) < 15_000:  # 太小多半是图标/占位
                raise RuntimeError(f"过小 {len(data)}B")
            it["file"] = os.path.basename(path)
            it["sha1_8"] = hashlib.sha1(data).hexdigest()[:8]
            with open(path, "wb") as fh:
                fh.write(data)
            done += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[dl-fail] {i} {type(exc).__name__} {str(exc)[:80]}", flush=True)
        if i % 25 == 0:
            print(f"[dl] {i}/{min(len(keep), args.max_download)}", flush=True)
        time.sleep(0.4)

    _dump_json(list_path, list(keep.values()))
    print(f"完成：下载 {done} 失败 {failed}；清单 {list_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
