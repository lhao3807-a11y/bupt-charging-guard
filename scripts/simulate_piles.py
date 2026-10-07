"""充电桩状态模拟器 CLI（PLAN §3.2 任务 5.8）。

把 `app/simulator.py` 的状态机接到**开发库**上，让第 3 页有会变的数据可看。

用法（仓库根目录）：:

    .venv\\Scripts\\python.exe scripts\\simulate_piles.py                # 推进一次
    .venv\\Scripts\\python.exe scripts\\simulate_piles.py --loop          # 每 10 秒推进一次（Ctrl+C 停）
    .venv\\Scripts\\python.exe scripts\\simulate_piles.py --loop --interval 3 --times 20
    .venv\\Scripts\\python.exe scripts\\simulate_piles.py --at 2026-09-08T10:30:00   # 快进到指定时刻（演示用）

**--at 是演示利器**：直接把「现在」设为若干小时后，桩会一次性走完
「充电中 → 已充满 → 超时释放」的流转，第 3 页三种状态色立刻都有样本。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import models as m
from app.db import SessionLocal, engine
from app.simulator import advance


def _snapshot(db) -> str:
    """一行式状态快照，便于肉眼确认「确实在变」。"""
    piles = db.query(m.ChargingPile).order_by(m.ChargingPile.pile_id.asc()).all()
    return " | ".join(f"{p.pile_id}={p.status}" for p in piles)


def _run_once(db, now: datetime | None) -> int:
    result = advance(db, now=now)
    stamp = result.advanced_at.strftime("%H:%M:%S")
    if not result.changes:
        print(f"[{stamp}] 无状态变化　{_snapshot(db)}")
        return 0
    for change in result.changes:
        print(
            f"[{stamp}] {change.pile_id}: {change.from_status} → {change.to_status}（{change.reason}）"
        )
    print(f"           {_snapshot(db)}")
    return result.changed_count


def main() -> int:
    parser = argparse.ArgumentParser(description="充电桩状态模拟器")
    parser.add_argument("--loop", action="store_true", help="循环推进（默认每 10 秒一次）")
    parser.add_argument("--interval", type=float, default=10.0, help="循环间隔秒数")
    parser.add_argument("--times", type=int, default=0, help="循环次数，0 = 不限（Ctrl+C 停）")
    parser.add_argument(
        "--at",
        default=None,
        help="把「现在」设为该时刻（ISO 8601，如 2026-09-08T10:30:00），用于演示快进",
    )
    args = parser.parse_args()

    fixed_now = datetime.fromisoformat(args.at) if args.at else None

    # 建表 + 灌种子：对着空库跑也能直接演示（种子 4 个桩覆盖三种状态）
    m.init_db(engine)
    db = SessionLocal()
    m.seed_db(db)
    try:
        if not args.loop:
            _run_once(db, fixed_now)
            return 0

        print(f"循环推进中（间隔 {args.interval}s，Ctrl+C 停止）")
        count = 0
        while args.times == 0 or count < args.times:
            # 循环模式下忽略 --at：时间自然流逝，便于观察真实节奏
            _run_once(db, None)
            count += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
