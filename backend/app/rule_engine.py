"""违规判断规则引擎 —— 对应 docs/CONTRACT.md §6.2 `/api/judge` 与开发大纲 M5。

四条规则（开发大纲 §5 / CONTRACT §3.3 的 rule_hit 取值）：

    ==========  ====================================================  ==============
    规则        判定条件                                              rule_hit
    ==========  ====================================================  ==============
    ① 燃油占位  车牌为燃油牌（蓝牌）且车停在充电桩上                    1
    ② 异常占位  新能源车停在桩上但未充电（status=空闲），
                且久停时长 > abnormal_park_min                       2
    ③ 充满未移  新能源车桩已充满，且充满后时长 > full_timeout_min       3
    ④ 正常充电  其余情况（充电中 / 充满未超时 / 刚停下未超阈值）        返回 None
    ==========  ====================================================  ==============

判定口径（经 CONTRACT 逐条确认，改动须先改契约并升版本号）：

1. **桩关联**：入参 ``RecognitionResult`` 不含桩信息，引擎按 ``plate``
   反查 ``charging_pile.bound_plate`` 得到车辆所在桩。查不到桩 → 该车未停在
   充电位上，不属于本系统判定范围，返回 ``None``。
2. **时间基准**：以 ``RecognitionResult.frame_time`` 作为判定「现在」的时刻，
   使引擎不依赖真实系统时钟、可被测试完全控制。
3. **久停时长**：``charging_pile.start_time`` 复用为「车辆绑定 / 到达该桩的时间」，
   新能源车未充电时以此计算久停时长。
4. **阈值**：``full_timeout_min`` / ``abnormal_park_min`` 一律从 ``system_config``
   读取，**严禁硬编码**（CONTRACT §7）。

维护人：汤瑾睿
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m
from app.schemas import NotifyStatus, RecognitionResult, ViolationRecord


class ConfigMissingError(RuntimeError):
    """system_config 缺少必需参数 —— 契约 §7 要求阈值必须来自该表。"""


def get_config_int(db: Session, key: str) -> int:
    """从 system_config 读取整型参数；缺失则抛出明确异常（不静默兜底）。"""
    row = db.query(m.SystemConfig).filter(m.SystemConfig.key == key).one_or_none()
    if row is None:
        raise ConfigMissingError(
            f"system_config 缺少参数 {key!r}：请确认已执行 backend/sql/schema.sql 的种子数据"
        )
    try:
        return int(row.value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - 数据错误路径
        raise ConfigMissingError(f"system_config.{key} 的值 {row.value!r} 不是合法整数") from exc


def find_pile_by_plate(db: Session, plate: str) -> m.ChargingPile | None:
    """按车牌反查车辆所在桩（口径 1：bound_plate）。"""
    return db.query(m.ChargingPile).filter(m.ChargingPile.bound_plate == plate).one_or_none()


def _elapsed_minutes(since: datetime, now: datetime) -> float:
    """返回 since → now 的分钟数（负值按 0 处理，避免时钟回拨误判）。"""
    return max((now - since).total_seconds() / 60.0, 0.0)


def judge(
    recognition: RecognitionResult,
    db: Session,
    *,
    now: datetime | None = None,
) -> ViolationRecord | None:
    """识别结果 → 违规判定。

    :param recognition: 识别结果（真实 CV 或识别桩 stub，结构一致）。
    :param db: SQLAlchemy 会话（引擎内部查 charging_pile 与 system_config）。
    :param now: 判定时刻，默认取 ``recognition.frame_time``；显式传入便于测试。

    :return: 命中规则①/②/③ 时返回**尚未落库**的 ``ViolationRecord``（``id`` 为 ``None``）；
             命中规则④（正常）返回 ``None``。
    """
    moment = now or recognition.frame_time
    pile = find_pile_by_plate(db, recognition.plate)

    # 车不在任何充电桩上 → 非本系统判定范围
    if pile is None:
        return None

    rule_hit = _decide_rule(recognition, pile, db, moment)
    if rule_hit is None:
        return None

    return ViolationRecord(
        id=None,
        plate=recognition.plate,
        vtype=recognition.vtype,
        pile_id=pile.pile_id,
        rule_hit=rule_hit,
        occur_time=moment,
        notify_status=NotifyStatus.未提醒,
    )


def _decide_rule(
    recognition: RecognitionResult,
    pile: m.ChargingPile,
    db: Session,
    moment: datetime,
) -> int | None:
    """四条规则的核心判定，返回 rule_hit 或 None（正常/无法判定）。"""
    # 规则①：燃油车（蓝牌）占充电位 —— 只看车型，不看桩状态
    if recognition.vtype == m.VTYPE_FUEL:
        return m.RULE_FUEL_OCCUPY

    # 以下均为新能源车
    if pile.status == m.PILE_IDLE:
        # 规则②：停在桩上却未充电，且久停超过阈值
        if pile.start_time is None:
            return None  # 无到达时间，无法判定久停
        threshold = get_config_int(db, "abnormal_park_min")
        if _elapsed_minutes(pile.start_time, moment) > threshold:
            return m.RULE_ABNORMAL
        return None

    if pile.status == m.PILE_FULL:
        # 规则③：已充满，且充满后超时未移车
        if pile.end_time is None:
            return None  # 无充满时间，无法判定超时
        threshold = get_config_int(db, "full_timeout_min")
        if _elapsed_minutes(pile.end_time, moment) > threshold:
            return m.RULE_FULL_NOT_MOVED
        return None

    # 规则④：充电中 → 正常，不提醒
    return None


# ---------------------------------------------------------------------------
# 落库 / 沙箱辅助（供 /api/judge、/api/notify 路由复用）
# ---------------------------------------------------------------------------
def save_violation(db: Session, record: ViolationRecord) -> ViolationRecord:
    """把违规记录落库，返回带 ``id`` 的记录；**同一违规复用已有记录**。

    落库口径（2026-09-13 与吕浩对齐，写入 CONTRACT §6.2）：

    - ``/api/judge`` 命中即落库（非等 ``/api/notify``）。
    - **去重**：若已存在 ``pile_id`` + ``rule_hit`` 相同且 ``notify_status='未提醒'``
      的记录，视为「同一违规持续中」——更新其 ``occur_time`` 后返回原记录，
      **不新增行**。避免轮询场景下记录爆炸、保证「报警统计」页数字真实。
    - 已提醒过（``notify_status != '未提醒'``）或规则已变（``rule_hit`` 不同）
      则视为新违规，新增一条。
    """
    existing = (
        db.query(m.OccupationRecord)
        .filter(
            m.OccupationRecord.pile_id == record.pile_id,
            m.OccupationRecord.rule_hit == record.rule_hit,
            m.OccupationRecord.notify_status == m.NOTIFY_PENDING,
        )
        .order_by(m.OccupationRecord.id.desc())
        .first()
    )

    if existing is not None:
        existing.occur_time = record.occur_time
        existing.plate = record.plate
        existing.vtype = record.vtype
        db.commit()
        db.refresh(existing)
        return ViolationRecord(
            id=existing.id,
            plate=existing.plate,
            vtype=existing.vtype,
            pile_id=existing.pile_id,
            rule_hit=existing.rule_hit,
            occur_time=existing.occur_time,
            notify_status=existing.notify_status,
        )

    row = m.OccupationRecord(
        plate=record.plate,
        vtype=record.vtype,
        pile_id=record.pile_id,
        rule_hit=record.rule_hit,
        occur_time=record.occur_time,
        notify_status=record.notify_status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return record.model_copy(update={"id": row.id})


def mark_notified(
    db: Session,
    record_id: int,
    status: str,
    when: datetime | None = None,
) -> bool:
    """短信沙箱：按记录 ``id`` 更新提醒状态与时间。返回是否找到该记录。

    入参口径（2026-09-13 与吕浩对齐，写入 CONTRACT §6.3）：``/api/notify``
    请求体为 ``{"id": <int>, "notify_status": "已提醒"}``，``id`` 取自
    ``/api/judge`` 返回的记录——沙箱据此定位要更新的行。
    """
    row = db.get(m.OccupationRecord, record_id)
    if row is None:
        return False
    row.notify_status = status
    row.notify_time = when or datetime.now()
    db.commit()
    return True
