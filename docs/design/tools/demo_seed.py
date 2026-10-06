"""答辩素材用的演示数据生成器（配合 `demo_screenshots.py`，第 2 周任务 6.10）。

为什么需要它
------------------------------------------------------------------------
`demo_screenshots.py` 拍的是**真实运行的界面**，所以第 1/2 页必须先有数据可看。
第 1 页（车辆）有种子数据，第 2 页（违规记录）**没有** —— 契约里违规记录只能由
`/api/judge` 命中后落库，库里默认是空的（种子不写 `occupation_record`）。

于是这里按契约端点把闭环跑一遍：

    POST /api/recognize  →  POST /api/judge  →  POST /api/notify

三条硬约束（与 `walkthrough.md` 的纪律一致）：
  1. **不直连数据库、不改 SQL、不动前端 mock** —— 只打契约端点，走系统自己的口径；
  2. 记录的 `occur_time` 取自 `/api/judge` 的 `frame_time`（引擎定义「判定时刻」的方式），
     所以**不需要改系统时钟**就能造出跨越几天的记录；
  3. 提醒状态用 `/api/notify` 改，不手改字段 —— 这样第 2 页三种状态都有真实来源。

用法（仓库根目录，后端已起）：
    python docs/design/tools/demo_seed.py
    python docs/design/tools/demo_seed.py --base http://127.0.0.1:8000

⚠️ 幂等性说明：引擎对「同一桩 + 同一规则 + **仍未提醒**」的记录会复用（不新增行）。
   因此重复执行本脚本会按「新违规」口径**追加**记录。想要干净的一套数据，
   先停后端、删掉开发库 `backend/app.db`（gitignore 的可再生产物）、再重启后端
   （启动时自动建表 + 灌种子），然后跑本脚本。
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

# 本机服务不吃代理 —— 与 scripts/e2e_check.py 同一条纪律（否则 URL 会被代理重写）
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

# 车牌 → 桩 的绑定来自后端种子（backend/sql/schema.sql），不能自造：
#   • 京A88888  燃油   → PILE-004 空闲    → 规则① 燃油车占位
#   • 京AD24680 新能源 → PILE-003 空闲    → 规则② 异常占位（久停 > abnormal_park_min）
#   • 京AD67890 新能源 → PILE-002 已充满  → 规则③ 充满未移车（充满 > full_timeout_min）
# `frame_time` 就是引擎眼中的「现在」，故用不同的 frame_time 造出跨越几天的记录。
DEMO: list[tuple[str, str, str, str]] = [
    ("京A88888", "燃油", "2026-10-01T09:12:00", "已提醒"),
    ("京A88888", "燃油", "2026-10-03T08:40:00", "已提醒"),
    ("京A88888", "燃油", "2026-10-05T10:30:00", ""),
    ("京AD24680", "新能源", "2026-10-01T14:05:00", "失败"),
    ("京AD24680", "新能源", "2026-10-04T16:20:00", "已提醒"),
    ("京AD24680", "新能源", "2026-10-05T09:50:00", ""),
    ("京AD67890", "新能源", "2026-10-02T11:30:00", "已提醒"),
    ("京AD67890", "新能源", "2026-10-04T13:15:00", "已提醒"),
    ("京AD67890", "新能源", "2026-10-05T15:40:00", "已提醒"),
]

BBOX = [96, 280, 452, 356]


def main() -> int:
    ap = argparse.ArgumentParser(description="生成答辩素材用的演示数据（走契约端点）")
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="后端地址")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(timeout=15) as client:
        try:
            health = client.get(f"{base}/api/health")
            health.raise_for_status()
        except httpx.HTTPError as exc:
            sys.exit(f"后端不可达 {base} —— {exc}\n请先起后端：cd backend && uvicorn app.main:app --port 8000")

        print("后端 %s / api/health = %s" % (base, health.json()))

        created: list[str] = []
        for plate, vtype, frame_time, notify in DEMO:
            payload = {
                "plate": plate,
                "vtype": vtype,
                "confidence": 0.97,
                "bbox": BBOX,
                "frame_time": frame_time,
            }
            r = client.post(f"{base}/api/judge", json=payload)
            if r.status_code != 200:
                sys.exit(f"judge 失败 {r.status_code}：{r.text[:200]}")
            record = r.json()
            if record is None:
                sys.exit(f"{plate} @ {frame_time} 判定为规则④（正常），不落库 —— 请检查种子绑定")
            rid = record["id"]
            status_text = "未提醒（不调 notify）"
            if notify:
                nr = client.post(f"{base}/api/notify", json={"id": rid, "notify_status": notify})
                if nr.status_code != 200:
                    sys.exit(f"notify 失败 {nr.status_code}：{nr.text[:200]}")
                status_text = notify
            print(
                "  + id=%-3s %-10s %-9s %-7s rule_hit=%s  %s"
                % (rid, record["plate"], record["pile_id"], record["occur_time"][:16], record["rule_hit"], status_text)
            )
            created.append(str(rid))

        page = client.get(f"{base}/api/records", params={"page": 1, "size": 20}).json()
        print("\n本次涉及记录 id：%s" % ", ".join(created))
        print("records 总数：%s" % page["total"])
        for item in page["items"]:
            print(
                "  id=%-3s rule_hit=%s %-9s %-7s %s"
                % (item["id"], item["rule_hit"], item["plate"], item["pile_id"], item["notify_status"])
            )

    print(
        "\n提醒：手机号由前端 maskPhone 脱敏；**车牌按「不打码」口径执行**（walkthrough §11 的 R9 决策）。"
        "\n下一步：python docs/design/tools/demo_screenshots.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
