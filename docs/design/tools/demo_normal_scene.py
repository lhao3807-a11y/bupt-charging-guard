#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W6-03 · 正常充电不落库、统计不变的接口凭据。

背景
----
复核指出（WEEK3_WU_REWORK 第 20 行）：正常场景在演示材料里是「间接覆盖」，
「不能以缺少表格行冒充运行画面」。本脚本给出**可复现的接口证据链**：

    1. 取一条「正常充电」的车（PILE-001 充电中 + 新能源 → 规则 ④）
    2. 对它调 POST /api/judge，断言返回 **null**（即不产生违规记录）
    3. 比对调用前后 GET /api/records 的 total —— **不变**
    4. 比对调用前后 GET /api/stats 的 total 与 by_rule[0]（正常充电）—— **均不变**
    5. 脚本不请求 POST /api/notify；未监测服务端发送器，不独立证明发送次数。

对应计划 §5 A04：「正常充电/未超时/无车：不生成违规，不调用发送器，不增加违规统计」。

用法
----
    python docs/design/tools/demo_normal_scene.py            # 打印证据
    python docs/design/tools/demo_normal_scene.py --json     # 追加写 JSON 凭据

JSON 输出到 ``docs/acceptance/week3/A04-normal-scene.json``。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
API = os.environ.get("DEMO_API_URL", "http://127.0.0.1:8000")
OUT_DIR = ROOT / "docs" / "acceptance" / "week3"


def snapshot(c: httpx.Client) -> dict:
    """取「记录总数」与「统计口径」两个可比快照。"""
    rec = c.get(f"{API}/api/records", params={"page": 1, "size": 1}).json()
    st = c.get(f"{API}/api/stats", params={"days": 90}).json()
    normal = next((x for x in st["by_rule"] if x["rule_hit"] == 0), None)
    return {
        "records_total": rec["total"],
        "stats_total": st["total"],
        "by_rule_normal_charge": normal["count"] if normal else None,
    }


def main() -> int:
    c = httpx.Client(trust_env=False, timeout=10)

    # ① 找一个「正常」组合：状态=充电中 且 车型=新能源 → 规则 ④
    piles = c.get(f"{API}/api/piles").json()["items"]
    vehicles = c.get(f"{API}/api/vehicles", params={"page": 1, "size": 50}).json()["items"]
    vmap = {v["plate"]: v for v in vehicles}

    normal_pile = None
    for p in piles:
        if p["status"] == "充电中" and p["bound_plate"] in vmap:
            if vmap[p["bound_plate"]]["vtype"] == "新能源":
                normal_pile = p
                break
    if normal_pile is None:
        sys.exit("演示库里没有「充电中 + 新能源」的桩，无法演示正常场景。")

    plate = normal_pile["bound_plate"]
    print(f"正常场景对象：车牌 {plate}（{vmap[plate]['vtype']}） @ {normal_pile['pile_id']}"
          f"（{normal_pile['status']}）")
    print("判定口径：规则 ④ 正常充电 → 应返回 null、不落库\n")

    before = snapshot(c)
    print("调用前快照：", json.dumps(before, ensure_ascii=False))

    # ② 对正常场景调 judge —— 期望 null
    payload = {
        "plate": plate,
        "vtype": vmap[plate]["vtype"],
        "confidence": 0.97,
        "bbox": [120, 80, 200, 120],
        "frame_time": datetime.now().replace(microsecond=0).isoformat(),
    }
    resp = c.post(f"{API}/api/judge", json=payload)
    resp.raise_for_status()
    verdict = resp.json()

    print(f"\nPOST /api/judge → HTTP {resp.status_code}")
    print(f"响应体：{json.dumps(verdict, ensure_ascii=False)}")

    after = snapshot(c)
    print("调用后快照：", json.dumps(after, ensure_ascii=False))

    # ③ 三条断言
    checks = [
        ("规则 ④ 返回 null（不产生违规记录）", verdict is None),
        ("违规记录总数不变", before["records_total"] == after["records_total"]),
        ("统计总数不变", before["stats_total"] == after["stats_total"]),
        ("「正常充电」分项计数不变", before["by_rule_normal_charge"] == after["by_rule_normal_charge"]),
    ]
    print("\n断言结果：")
    ok = True
    for name, passed in checks:
        print(f"  {'✓' if passed else '✗'} {name}")
        ok &= passed

    print("\n说明：本脚本**全程未调用 POST /api/notify**（发送器），"
          "未监测服务端发送器，此项需结合后端 A04 行为测试。")

    if "--json" in sys.argv:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / "A04-normal-scene.json"
        out.write_text(json.dumps({
            "task": "W6-03",
            "acceptance": "A04 正常充电/未超时/无车：不生成违规，不调用发送器，不增加违规统计",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "env": {"api": API, "db": os.environ.get("DEMO_DATABASE_LABEL", "由服务端 DATABASE_URL 指定，脚本未读取连接配置")},
            "command": "python docs/design/tools/demo_normal_scene.py --json",
            "request": {"method": "POST", "path": "/api/judge", "body": payload},
            "response": {"status": resp.status_code, "body": verdict},
            "before": before,
            "after": after,
            "checks": {n: bool(p) for n, p in checks},
            "notify_observation": "本脚本未调用提醒端点；未监测服务端发送器，不作为发送次数证据",
            "all_passed": bool(ok),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n凭据已写入：{out.relative_to(ROOT)}")

    print("\n结论：" + ("全部通过，正常场景不落库且统计不变" if ok else "存在不通过项，见上"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
