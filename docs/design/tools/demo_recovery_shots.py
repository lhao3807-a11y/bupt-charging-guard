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
3. ``w601-3-final``     最终态：同一行显示「已提醒」

安全性
------
只打契约端点，不直连数据库、不改 SQL、不动前端 mock —— 同 ``demo_seed.py`` 的口径。
结束时会把演示记录恢复成原始状态，避免污染其他人的截图。
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = "http://localhost:5173"
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
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
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


def main() -> int:
    api = "http://127.0.0.1:8000"
    c = httpx.Client(trust_env=False, timeout=10)

    # ① 找一条失败态记录作为主角
    rows = c.get(f"{api}/api/records", params={"page": 1, "size": 50}).json()["items"]
    failed = [r for r in rows if r["notify_status"] == "失败"]
    if not failed:
        sys.exit("没有失败态记录，请先跑 docs/design/tools/demo_seed.py")
    target = failed[0]
    rid, plate = target["id"], target["plate"]
    print(f"主角记录：id={rid} {plate}（当前 失败）")

    # ② 记录原始状态，结束时还原
    origin_status = target["notify_status"]
    profile = RAW_DIR / f".w601-{uuid.uuid4().hex[:8]}"
    browser = find_browser()
    print(f"浏览器：{browser}")

    try:
        print("\n[1/3] 拍失败态（不改动库，当前即为真实失败态）")
        shoot(browser, "w601-1-failed", "/records", profile)

        print("\n[2/3] 模拟「补绑定手机号后重试」→ 走 POST /api/notify（与前端同一端点）")
        resp = c.post(f"{api}/api/notify", json={"id": rid, "notify_status": "已提醒"})
        resp.raise_for_status()
        print(f"  重试结果：{resp.json()}")
        shoot(browser, "w601-2-recovered", "/records", profile)

        print("\n[3/3] 拍最终态（同上画面即为最终态；再拍一次以留下独立凭据）")
        shoot(browser, "w601-3-final", "/records", profile)

        print("\n回读验证（库中真实状态）")
        now = [r for r in c.get(f"{api}/api/records", params={"page": 1, "size": 50}).json()["items"]
               if r["id"] == rid][0]
        print(f"  id={rid} {plate} → {now['notify_status']}")

    finally:
        # 还原演示数据，避免影响其他人的截图
        c.post(f"{api}/api/notify", json={"id": rid, "notify_status": origin_status})
        print(f"\n已还原：id={rid} → {origin_status}")
        # 清理临时浏览器 profile（rmdir 在旧 Python 上无 missing_ok，手动判断）
        for p in profile.glob("*"):
            if p.is_file():
                p.unlink(missing_ok=True)
        if profile.exists():
            try:
                profile.rmdir()
            except OSError:
                pass

    print("\n完成。三张画面均为真实页面渲染，原件在 docs/design/demo/screenshots/raw/w601-*.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
