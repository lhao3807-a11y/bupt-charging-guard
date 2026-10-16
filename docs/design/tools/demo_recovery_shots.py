#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W6-01 · 拍「发送失败 → 恢复 → 重试成功」的真实画面（计划 W6 · 任务 W6-01）。

背景
----
计划 W6 要求演示素材包含「发送失败后恢复」。W6 交付时只给了**静态失败态**截图，
被复核判为「缺失败后恢复的连续操作画面」。本脚本补这一段。

为什么用「接口驱动 + 分步拍摄」而不是「自动点击」
------------------------------------------
仓库自带的 ``demo_screenshots.py`` 用 Edge 无头模式只能拍静态路由，不能点按钮
（``agent-browser`` daemon 在本机环境无法稳定启动，见 walkthrough §17）。
但前端「重试」按钮最终调的就是 ``POST /api/notify``（见 ``RecordsView.vue:67``
→ ``stores/records.ts:84``），与本脚本直接调用的是**同一个端点**。

因此本脚本拍出的画面是**真实页面渲染**，与人工点击的结果一致；
差别只在「谁来触发那一次请求」。**这个差别会写进文档，不含糊过去** ——
它不是「录屏」，是「同端点驱动的状态前后对比」。

三张画面
--------
1. ``w601-1-failed``    失败态：某条记录 ``notify_status='失败'``，行内按钮为「重试」
2. ``w601-2-recovered`` 恢复后：手机号补齐（同一辆车），重试成功 → ``已提醒``
3. ``w601-3-final``     重复请求命中已有结果，计数不增加

安全性
------
只打契约端点，不直连数据库、不改 SQL、不动前端 mock —— 同 ``demo_seed.py`` 的口径。
仅用于独立演示库；成功后的发送状态与次数保留，不倒写失败状态。
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = os.environ.get("DEMO_FRONTEND_URL", "http://localhost:5173")
RAW_DIR = ROOT / "docs" / "design" / "demo" / "screenshots" / "raw"
VIEWPORT = (1600, 880)

BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
    for p in BROWSER_CANDIDATES:
        if Path(p).exists():
            return p
    sys.exit("未找到 Chrome / Edge，无法拍摄。")


def shoot(browser: str, name: str, route: str, profile: Path) -> Path:
    """拍一张真实页面（与 demo_screenshots.shoot 同口径：同视口、同虚拟时间预算）。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / f"{name}.png"
    fresh = RAW_DIR / f"{name}.{uuid.uuid4().hex}.fresh.png"
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        f"--user-data-dir={profile}",
        f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}",
        # 与既有脚本同值：第 2 页是 SPA，少了这个会拍到「骨架在、内容空白」。
        "--virtual-time-budget=10000",
        f"--screenshot={fresh}",
        FRONTEND + route,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if proc.returncode != 0 or not fresh.exists():
        fresh.unlink(missing_ok=True)
        sys.exit(f"拍摄失败：{route}\n{(proc.stderr or proc.stdout)[-600:]}")
    fresh.replace(target)
    print(f"  拍 {name:<22} {route} → {target.relative_to(ROOT)}")
    return target


def recover_record(c, api: str, target: dict, phone: str, capture) -> dict:
    """只接受 v1.9 发送器结果；错误时不拍成功画面、不回退记录状态。"""
    rid = target["id"]
    response = c.post(f"{api}/api/notify", json={"id": rid, "retry": False})
    response.raise_for_status()
    before = response.json()
    if "notify_attempts" not in before:
        raise ValueError("需要 v1.9 后端；旧版直接写提醒状态不能作为恢复证据")
    if before["notify_status"] != "失败" or before.get("reason") != "车主未绑定手机号":
        raise ValueError("请选择因车主未绑定手机号失败的专用演示记录")
    capture("w601-1-failed")
    response = c.put(
        f"{api}/api/vehicles/{target['plate']}", json={"vtype": target["vtype"], "phone": phone}
    )
    response.raise_for_status()
    response = c.post(f"{api}/api/notify", json={"id": rid, "retry": True})
    response.raise_for_status()
    recovered = response.json()
    if (
        recovered.get("id") != rid
        or recovered.get("notify_status") != "已提醒"
        or recovered.get("notify_attempts") != before["notify_attempts"] + 1
        or recovered.get("already_sent")
        or recovered.get("exhausted")
        or recovered.get("conflict")
    ):
        raise ValueError(f"重试未成功，不生成成功截图：{recovered}")
    capture("w601-2-recovered")
    response = c.post(f"{api}/api/notify", json={"id": rid, "retry": True})
    response.raise_for_status()
    final = response.json()
    if (
        final.get("id") != rid
        or final.get("notify_status") != "已提醒"
        or not final.get("already_sent")
        or final.get("notify_attempts") != recovered["notify_attempts"]
    ):
        raise ValueError("重复请求未命中已有结果，不生成最终截图")
    capture("w601-3-final")
    return {"record_id": rid, "before": before, "recovered": recovered, "final": final}


def main() -> int:
    import argparse
    import json
    import tempfile
    from datetime import datetime

    parser = argparse.ArgumentParser(
        description="v1.9 无手机号失败→补绑定→真实重试；仅用于独立演示环境"
    )
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--record-id", type=int, required=True)
    parser.add_argument("--phone", required=True)
    parser.add_argument(
        "--demo-only", action="store_true", help="确认连接独立演示库；会保留发送成功状态"
    )
    args = parser.parse_args()
    if not args.demo_only:
        parser.error("必须使用独立演示库并传 --demo-only；不可回滚已发送记录伪造失败状态")
    browser = find_browser()
    with httpx.Client(trust_env=False, timeout=10) as c, tempfile.TemporaryDirectory() as temp:
        response = c.get(f"{args.api}/api/records", params={"page": 1, "size": 100})
        response.raise_for_status()
        target = next((r for r in response.json()["items"] if r["id"] == args.record_id), None)
        if target is None:
            raise ValueError("未找到演示记录，请使用前 100 条中的失败记录")
        result = recover_record(
            c,
            args.api,
            target,
            args.phone,
            lambda name: shoot(browser, name, "/records", Path(temp)),
        )
        result.update(
            generated_at=datetime.now().isoformat(),
            mode="sandbox",
            api=args.api,
            capture="API 驱动真实运行态分步截图，非人工点击录屏",
        )
        # 短信内容含车主信息，验收文件只留状态与计数。
        for key in ("before", "recovered", "final"):
            result[key].pop("message", None)
        out = ROOT / "docs/acceptance/week3/W6-01-recovery.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成：成功状态保留在专用演示库；未回滚发送历史。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
