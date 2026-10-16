"""第三周演示夹具：把桩摆成四个**确定性**场景（T5 / 验收 A02–A04）。

为什么需要它：默认模拟流程是「空闲 → 3 分钟后自动开始充电 → 20 分钟充满」，
用它演示默认 30 分钟的久停阈值得**干等半小时**，而且空闲桩会在演示开始就被推进成
「充电中」，规则②根本没机会出现。本脚本直接把桩摆到位，**不为了演示改业务阈值**。

用法（仓库根目录）：

```powershell
.venv\\Scripts\\python.exe scripts\\seed_week3_demo.py                      # 四个场景一次摆好
.venv\\Scripts\\python.exe scripts\\seed_week3_demo.py --scenario idle      # 只摆「未充电久停」
.venv\\Scripts\\python.exe scripts\\seed_week3_demo.py --at 2026-09-08T10:00:00
.venv\\Scripts\\python.exe scripts\\seed_week3_demo.py --elapsed 31         # 久停/超时已过 31 分钟
.venv\\Scripts\\python.exe scripts\\seed_week3_demo.py --reset              # 清掉四个演示桩
```

**确定性**：时间基准一律以 `--at`（默认当前时刻）为「现在」往前推，不读系统时钟做判定，
所以「同样的输入和时刻」必然得到「同样的结果」（A12 的通过标准）。

⚠️ 会写**当前 DATABASE_URL 指向的库**。演示请用独立库，别指向有数据的开发库。
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import charging_adapter as ca
from app import models as m
from app import occupancy
from app.db import SessionLocal, engine
from app.rule_engine import judge
from app.schemas import RecognitionResult

#: 演示桩 → （场景，车牌）。车牌取自种子车辆（schema.sql），保证车型与场景要求一致
DEMO_PILES: tuple[tuple[str, str, str], ...] = (
    ("PILE-D1", ca.SCENARIO_FUEL, "京A88888"),  # 燃油 → 规则①
    ("PILE-D2", ca.SCENARIO_IDLE, "京AD24680"),  # 新能源久停 → 规则②
    ("PILE-D3", ca.SCENARIO_FULL, "京AD67890"),  # 新能源充满超时 → 规则③
    ("PILE-D4", ca.SCENARIO_NORMAL, "京AD12345"),  # 正常充电 → 规则④（不违规）
)

_RULE_LABELS = {1: "① 燃油占位", 2: "② 异常占位", 3: "③ 充满未移车", 0: "④ 正常（不违规）"}


def _ensure_pile(db, pile_id: str) -> m.ChargingPile:
    row = db.get(m.ChargingPile, pile_id)
    if row is None:
        row = m.ChargingPile(pile_id=pile_id, status=m.PILE_IDLE)
        db.add(row)
        db.commit()
    return row


def _expected_rule(db, pile: m.ChargingPile, at: datetime) -> int | None:
    """按当前桩状态预演一次判定（只读，不落库）。

    返回 `0` = 规则④ 正常（不违规），`1/2/3` = 命中对应规则，
    `None` = **无法判定**（车没录入 / 没绑桩）—— 与「正常」区分开，
    否则演示时会把「数据没准备好」说成「正常」，正是最容易被误读的一句。
    """
    vehicle = db.get(m.Vehicle, pile.bound_plate) if pile.bound_plate else None
    if vehicle is None:
        return None
    hit = judge(
        RecognitionResult(
            plate=pile.bound_plate,
            vtype=vehicle.vtype,
            confidence=1.0,
            bbox=[0, 0, 0, 0],
            frame_time=at,
        ),
        db,
        now=at,
    )
    return 0 if hit is None else hit.rule_hit


def _unbind_elsewhere(db, plate: str, keep_pile_id: str) -> int:
    """把同一车牌从**别的桩**上摘掉，返回摘掉的桩数。

    规则引擎按「车牌 → 桩」反查（`find_pile_by_plate`），同一车牌绑在两处会直接
    `MultipleResultsFound`。种子桩（PILE-001..004）本来就绑着这几块演示车牌，
    所以夹具**必须**先清理 —— 这是夹具的责任，不是判定逻辑该操心的。
    """
    freed = 0
    for other in db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == plate).all():
        if other.pile_id == keep_pile_id:
            continue
        occupancy.end_occupancy(other)
        freed += 1
    db.commit()
    return freed


def seed(db, scenario: str, at: datetime, overshoot: int | None) -> int:
    count = 0
    for pile_id, scen, plate in DEMO_PILES:
        if scenario != "all" and scen != scenario:
            continue
        pile = _ensure_pile(db, pile_id)
        _unbind_elsewhere(db, plate, keep_pile_id=pile_id)
        ca.apply_scenario(pile, plate, scen, at, db, overshoot_min=overshoot)
        rule = _expected_rule(db, pile, at)
        print(
            f"  {pile_id}  {ca.SCENARIO_LABELS[scen]:<6}  {plate}  "
            f"status={pile.status}  start={pile.start_time}  end={pile.end_time}  "
            f"→ {_RULE_LABELS.get(rule, '（无法判定）')}"
        )
        count += 1
    return count


def reset(db) -> int:
    count = 0
    for pile_id, _, _ in DEMO_PILES:
        pile = db.get(m.ChargingPile, pile_id)
        if pile is None:
            continue
        db.delete(pile)
        count += 1
    db.commit()
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="第三周四场景演示夹具")
    parser.add_argument(
        "--scenario",
        default="all",
        help=f"场景：all / {' / '.join(ca.SCENARIOS)}",
    )
    parser.add_argument(
        "--at", default=None, help="把「现在」设为该时刻（ISO 8601），默认取系统时钟"
    )
    parser.add_argument(
        "--elapsed",
        type=int,
        default=None,
        help="久停/超时已过去的分钟数；不给则用「阈值 + 10 分钟」（阈值查 system_config）",
    )
    parser.add_argument("--reset", action="store_true", help="删除四个演示桩（不碰其他数据）")
    args = parser.parse_args()

    if args.scenario != "all" and args.scenario not in ca.SCENARIOS:
        parser.error(f"未知场景：{args.scenario}（可选 all / {' / '.join(ca.SCENARIOS)}）")

    at = datetime.fromisoformat(args.at) if args.at else datetime.now()

    m.init_db(engine)
    db = SessionLocal()
    try:
        m.seed_db(db)  # 保证 vehicle / system_config 存在（已存在则跳过）
        if args.reset:
            print(f"已删除 {reset(db)} 个演示桩")
            return 0
        print(f"演示基准时刻：{at.isoformat()}")
        count = seed(db, args.scenario, at, args.elapsed)
        print(f"\n已布置 {count} 个场景。下一步：POST /api/judge 或直接跑 scripts/run_pipeline.py")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
