"""端到端闭环验证脚本（真实 HTTP，非 TestClient）。

用途：本地起服务后手跑一遍「识别 → 判定 → 提醒 → 后台可查」，
确认契约 §11 的 Demo 主线在真实进程里成立。

用法（仓库根目录下）：
    .venv\\Scripts\\python.exe scripts\\e2e_check.py [base_url]
需先启动服务：cd backend && ..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import os
import sys

import httpx

# 沙箱/本机若设了 http_proxy，httpx 会把本地请求也经代理发出、URL 被错误重写
# （表现为日志里出现 "POST http%3A//127.0.0.1%3A8000/api/..." 并返回 404）。
# 本脚本只打本机服务，直接禁用代理。
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

# 真实标注映射（algo/samples/labels）：004=新能源充满 → 规则③；002=燃油 → 规则①
FRAME = "004.jpg"
FUEL_PLATE = {
    "plate": "京A88888",
    "vtype": "燃油",
    "confidence": 0.96,
    "bbox": [128, 300, 468, 372],
    "frame_time": "2026-09-08T10:00:00",
}


def main() -> int:
    client = httpx.Client(timeout=10)
    failures: list[str] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {label}" + (f"  {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    def url(path: str) -> str:
        return f"{BASE}{path}"

    print("=== 1) health ===")
    r = client.get(url("/api/health"))
    check("health == ok", r.status_code == 200 and r.json()["status"] == "ok", str(r.json()))

    print("=== 2) recognize（识别桩读标注） ===")
    r = client.post(url("/api/recognize"), json={"frame_ref": FRAME})
    check("recognize 200", r.status_code == 200, str(r.json()))
    recognition = r.json()

    print("=== 3) judge（命中规则③ 落库） ===")
    r = client.post(url("/api/judge"), json=recognition)
    violation = r.json()
    check(
        "judge 命中 rule_hit=3",
        r.status_code == 200 and violation.get("rule_hit") == 3,
        str(violation),
    )
    check("judge 返回 id（已落库）", violation.get("id") is not None)
    rid = violation["id"]

    print("=== 4) notify（按 id 更新状态） ===")
    r = client.post(url("/api/notify"), json={"id": rid, "notify_status": "已提醒"})
    check("notify 200", r.status_code == 200, str(r.json()))

    print("=== 5) records（后台可查，状态已更新） ===")
    r = client.get(url("/api/records"), params={"page": 1, "size": 10})
    page = r.json()
    hit = next((it for it in page["items"] if it["id"] == rid), None)
    check("records.total >= 1", page["total"] >= 1, f"total={page['total']}")
    check(
        "records 含该记录且已提醒", hit is not None and hit["notify_status"] == "已提醒", str(hit)
    )

    print("=== 6) 容错：缺标注 → 404 ===")
    r = client.post(url("/api/recognize"), json={"frame_ref": "no_file.jpg"})
    check("recognize 缺文件 404", r.status_code == 404)

    print("=== 7) 容错：notify 未知 id → 404 ===")
    r = client.post(url("/api/notify"), json={"id": 999999, "notify_status": "已提醒"})
    check("notify 未知 id 404", r.status_code == 404)

    print("=== 8) 规则① 燃油占位 ===")
    r = client.post(url("/api/judge"), json=FUEL_PLATE)
    check(
        "judge 燃油 rule_hit=1", r.status_code == 200 and r.json()["rule_hit"] == 1, str(r.json())
    )

    client.close()

    print()
    if failures:
        print(f"FAILED: {len(failures)} 项未通过 -> {failures}")
        return 1
    print("ALL PASSED —— 端到端闭环在真实服务上成立")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
