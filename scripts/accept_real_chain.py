#!/usr/bin/env python
"""real 模式端到端验收：真实照片 → real CV 识别 → 判定 → 落库 → 沙箱发送。

**必须在算法环境里跑**（real CV 要 torch / ultralytics / hyperlpr3）：

```bash
.venv-algo\\Scripts\\python.exe scripts\\accept_real_chain.py
```

为什么单独一个脚本（返工清单 T3/T7 的要求）：`scripts/seed_week3_demo.py` 用**标注 JSON**
布场景，`scripts/run_pipeline.py` 默认 stub —— 两者都跑得通，但**都不能证明真实照片
走得通**。验收 A09/A10 明确要「real 模式从帧到落库/提醒的成功与失败实测」，
所以这里拿 `algo/dataset_web/` 的**网络实拍图**跑完整闭环，并把过程写成凭据。

覆盖的验收项：

| 项 | 本脚本怎么证明 |
|---|---|
| A01 自动闭环跑通 | 一轮 `Pipeline.run_once()` 完成 取帧→识别→判定→落库→发送 |
| A02 异常久停 | 实拍帧 + `idle_park` 场景 → 规则② |
| A03 充满未移车 | 实拍帧 + `full_timeout` 场景 → 规则③ |
| A04 正常充电不报警 | 实拍帧 + `normal` 场景 → 无违规、不落库 |
| A05 不重复提醒 | 第 2/3 轮 `newly_notified == 0`（第 3 轮换了进程） |
| A06 无手机号 | 燃油记录 → 失败且 `notify_attempts` 不增；补绑定后重试成功 |
| A07 失败重试 / 重启不清零 | 沙箱强制失败 → 重试成功；第 3 轮换进程后不重发 |
| A09 失败可见 | 坏图 / 无牌两帧 `error` 有原因，**不伪造识别结果** |
| A10 无串帧 | 逐帧核对「帧 → 车牌 → 桩」三元组与预期一致 |

产出：`docs/acceptance/week3/06-pipeline-real.{json,log}`

维护人：汤瑾睿
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(REPO, "backend")
for _path in (BACKEND, REPO):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from app import charging_adapter as ca
from app import models as m
from app import notification
from app import pipeline as pl
from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

#: 实拍图来源（174 张网络实拍集，见 algo/dataset_web/README.md）
SRC_DIR = os.path.join(REPO, "algo", "dataset_web", "images", "val")

#: 这一张的 OCR 在实拍集上是空号码（实拍集已知短板），拿来当「无牌」失败样例
NO_PLATE_SRC = "web_0190.jpg"

#: 判定时刻固定，保证结果可复现（编排允许显式传 now）
JUDGE_NOW = datetime(2026, 10, 13, 15, 0, 0)

PHONE = "13800000001"

#: 场景 → 期望命中的规则（None = 正常，不违规）
EXPECTED_RULE: dict[str, int | None] = {
    ca.SCENARIO_FULL: m.RULE_FULL_NOT_MOVED,
    ca.SCENARIO_IDLE: m.RULE_ABNORMAL,
    ca.SCENARIO_NORMAL: None,
    ca.SCENARIO_FUEL: m.RULE_FUEL_OCCUPY,
}


@dataclass
class PlanRow:
    """一条「帧 → 场景」安排。"""

    dst: str  # 目标帧名（= frame_id）
    src: str  # 源实拍图文件名
    scenario: str
    plate: str
    vtype: str
    phone: str | None
    pile_id: str = ""
    is_fail_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "frame": self.dst,
            "pile_id": self.pile_id,
            "scenario": self.scenario,
            "scenario_label": ca.SCENARIO_LABELS[self.scenario],
            "plate": self.plate,
            "vtype": self.vtype,
            "phone": self.phone,
            "expected_rule": EXPECTED_RULE[self.scenario],
        }


@dataclass
class Log:
    lines: list[str] = field(default_factory=list)

    def __call__(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)


def _pick_candidates() -> list[str]:
    """按文件名升序取候选实拍图（排除已知无牌那张）。"""
    names = sorted(
        n for n in os.listdir(SRC_DIR) if n.lower().endswith(".jpg") and n != NO_PLATE_SRC
    )
    return names[:8]


def _probe(names: list[str]) -> list[dict]:
    """直接走算法链路识别候选图 —— 只为「挑车型」，端到端那遍会再走一次路由。"""
    from algo.recognize.plate import recognize_frame

    out: list[dict] = []
    for name in names:
        try:
            result = recognize_frame(os.path.join(SRC_DIR, name))
        except Exception as exc:  # noqa: BLE001 - 探测阶段容错，记下来即可
            out.append({"frame": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        out.append(
            {
                "frame": name,
                "plate": (result or {}).get("plate", ""),
                "vtype": (result or {}).get("vtype"),
                "confidence": (result or {}).get("confidence"),
            }
        )
    return out


def _setup_frames(root: str, rows: list[PlanRow]) -> str:
    """把选中实拍图复制进 `FRAME_SOURCE_DIR`，并额外造「无牌」「坏图」两帧。

    **失败演示那帧不进主目录**：它要用「恒失败」的发送器单独跑一轮，
    留在主目录会被正常轮次先成功发出去，后面就没得演示失败了。
    """
    frame_dir = os.path.join(root, "frames")
    os.makedirs(frame_dir, exist_ok=True)
    for row in rows:
        if row.is_fail_demo:
            continue
        shutil.copyfile(os.path.join(SRC_DIR, row.src), os.path.join(frame_dir, row.dst))
    # A09 样例①：OCR 空号码（真实照片，不是造出来的）
    shutil.copyfile(os.path.join(SRC_DIR, NO_PLATE_SRC), os.path.join(frame_dir, "z_noplate.jpg"))
    # A09 样例②：坏图（字节不是合法图片，解码必失败）
    with open(os.path.join(frame_dir, "z_corrupt.jpg"), "wb") as fh:
        fh.write(b"\xff\xd8\xff\xe0 not-a-real-jpeg " * 8)
    return frame_dir


def _register(session, plate: str, vtype: str, *, phone: str | None) -> None:
    row = session.get(m.Vehicle, plate)
    if row is None:
        session.add(
            m.Vehicle(plate=plate, vtype=vtype, owner="验收样例", phone=phone, created_at=JUDGE_NOW)
        )
    else:
        row.phone = phone
    session.commit()


def _dump_records(session) -> list[dict]:
    session.expire_all()
    rows = session.query(m.OccupationRecord).order_by(m.OccupationRecord.id).all()
    return [
        {
            "id": r.id,
            "plate": r.plate,
            "vtype": r.vtype,
            "pile_id": r.pile_id,
            "occupancy_id": r.occupancy_id,
            "rule_hit": r.rule_hit,
            "occur_time": r.occur_time.isoformat(),
            "notify_status": r.notify_status,
            "notify_time": r.notify_time.isoformat() if r.notify_time else None,
            "notify_attempts": r.notify_attempts,
            "notify_error": r.notify_error,
        }
        for r in rows
    ]


def _run_dict(run: pl.PipelineRun) -> dict:
    return run.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="real 模式端到端验收")
    parser.add_argument(
        "--json",
        default=os.path.join(REPO, "docs", "acceptance", "week3", "06-pipeline-real.json"),
    )
    parser.add_argument(
        "--log",
        default=os.path.join(REPO, "docs", "acceptance", "week3", "06-pipeline-real.log"),
    )
    args = parser.parse_args()

    log = Log()
    checks: list[dict] = []

    def check(key: str, desc: str, ok: bool, detail: str = "") -> None:
        checks.append({"id": key, "desc": desc, "pass": bool(ok), "detail": detail})
        log(f"  [{'PASS' if ok else 'FAIL'}] {key} {desc}" + (f" —— {detail}" if detail else ""))

    tmp = tempfile.mkdtemp(prefix="accept-real-")
    try:
        # ---- 阶段 1：探测车型，挑出能覆盖四场景的实拍图 -------------------
        log("=" * 78)
        log("阶段 1：实拍图识别探测（挑选场景素材）")
        log("=" * 78)
        probe = _probe(_pick_candidates())
        for item in probe:
            if "error" in item:
                log(f"  {item['frame']}  识别异常：{item['error']}")
                continue
            conf = item.get("confidence")
            conf_text = f"conf={conf:.3f}" if isinstance(conf, (int, float)) else ""
            log(
                f"  {item['frame']}  {item.get('plate') or '(空号)':<12} {item.get('vtype')}  {conf_text}"
            )

        fuel = next((p for p in probe if p.get("vtype") == m.VTYPE_FUEL and p.get("plate")), None)
        new_energy = [p for p in probe if p.get("vtype") == m.VTYPE_NEW_ENERGY and p.get("plate")]
        log(f"  挑中：燃油 {fuel['frame'] if fuel else '（无）'}；新能源 {len(new_energy)} 张")

        rows: list[PlanRow] = []
        if len(new_energy) >= 1:
            rows.append(
                PlanRow(
                    "a_full_timeout.jpg",
                    new_energy[0]["frame"],
                    ca.SCENARIO_FULL,
                    new_energy[0]["plate"],
                    m.VTYPE_NEW_ENERGY,
                    PHONE,
                )
            )
        if len(new_energy) >= 2:
            rows.append(
                PlanRow(
                    "b_idle_park.jpg",
                    new_energy[1]["frame"],
                    ca.SCENARIO_IDLE,
                    new_energy[1]["plate"],
                    m.VTYPE_NEW_ENERGY,
                    PHONE,
                )
            )
        if len(new_energy) >= 3:
            rows.append(
                PlanRow(
                    "c_normal.jpg",
                    new_energy[2]["frame"],
                    ca.SCENARIO_NORMAL,
                    new_energy[2]["plate"],
                    m.VTYPE_NEW_ENERGY,
                    PHONE,
                )
            )
        if len(new_energy) >= 4:
            rows.append(
                PlanRow(
                    "d_sandbox_fail.jpg",
                    new_energy[3]["frame"],
                    ca.SCENARIO_FULL,
                    new_energy[3]["plate"],
                    m.VTYPE_NEW_ENERGY,
                    PHONE,
                    is_fail_demo=True,
                )
            )
        if fuel:
            # 燃油那张**不绑手机号** —— 用来证明 A06（缺手机号不算尝试次数）
            rows.append(
                PlanRow(
                    "e_fuel.jpg", fuel["frame"], ca.SCENARIO_FUEL, fuel["plate"], m.VTYPE_FUEL, None
                )
            )

        # ---- 阶段 2：布置帧目录与数据库 -----------------------------------
        frame_dir = _setup_frames(tmp, rows)
        os.environ["FRAME_SOURCE_DIR"] = frame_dir
        os.environ["RECOGNITION_MODE"] = "real"
        os.environ.pop(notification.SANDBOX_RESULT_ENV, None)  # 主链路一律走「发送成功」

        engine = create_engine(f"sqlite:///{os.path.join(tmp, 'real.db')}", future=True)
        Base.metadata.create_all(bind=engine)
        boot = sessionmaker(bind=engine, future=True, autoflush=False)()
        m.seed_db(boot)
        boot.close()
        session = sessionmaker(bind=engine, future=True, autoflush=False)()

        # ---- 阶段 3：登记车辆 + 布场景 ------------------------------------
        log("")
        log("=" * 78)
        log("阶段 2：登记车辆（车牌/车型来自真实识别）+ 布置场景")
        log("=" * 78)
        bind_map: dict[str, str] = {}
        bind_map_fail: dict[str, str] = {}
        for idx, row in enumerate(rows, start=1):
            _register(session, row.plate, row.vtype, phone=row.phone)
            row.pile_id = f"PILE-R{idx}"
            pile = m.ChargingPile(pile_id=row.pile_id)
            session.add(pile)
            session.commit()
            ca.apply_scenario(pile, row.plate, row.scenario, JUDGE_NOW, session)
            if row.is_fail_demo:
                bind_map_fail[row.dst] = row.pile_id
            else:
                bind_map[row.dst] = row.pile_id
            log(
                f"  {row.dst:<22} {row.pile_id}  {ca.SCENARIO_LABELS[row.scenario]:<6} "
                f"{row.plate}  {row.vtype}  手机号={'有' if row.phone else '无'}  "
                f"期望 rule={EXPECTED_RULE[row.scenario]}"
            )

        fail_dir = os.path.join(tmp, "frames_fail")
        os.makedirs(fail_dir, exist_ok=True)
        for row in rows:
            if row.is_fail_demo:
                shutil.copyfile(os.path.join(SRC_DIR, row.src), os.path.join(fail_dir, row.dst))

        weights = __import__("algo.recognize.plate", fromlist=["DEFAULT_WEIGHTS"]).DEFAULT_WEIGHTS
        log(f"  权重：{os.path.relpath(weights, REPO)}")
        log(f"  取帧目录：{frame_dir}")

        # ---- 阶段 4：三轮闭环 --------------------------------------------
        log("")
        log("=" * 78)
        log("阶段 3：自动闭环（第 1 轮真识别 → 第 2 轮复用 → 第 3 轮换进程）")
        log("=" * 78)
        rounds: list[dict] = []

        pipe = pl.Pipeline(session, frame_dir=frame_dir, bind_map=bind_map)
        rounds.append(_run_dict(pipe.run_once(now=JUDGE_NOW)))
        # 第 2 轮：**同一个进程**，识别结果复用，但时间规则仍按 JUDGE_NOW 重判
        rounds.append(_run_dict(pipe.run_once(now=JUDGE_NOW)))

        # 第 3 轮：**换 Pipeline 实例 + 新会话**（等价进程重启，内存缓存清空）
        session2 = sessionmaker(bind=engine, future=True, autoflush=False)()
        pipe2 = pl.Pipeline(session2, frame_dir=frame_dir, bind_map=bind_map)
        rounds.append(_run_dict(pipe2.run_once(now=JUDGE_NOW)))

        for idx, run in enumerate(rounds, start=1):
            log(
                f"  第 {idx} 轮：帧 {run['frame_count']}  识别 {run['recognized']}  "
                f"复用 {run['skipped_unchanged']}  违规 {run['violations']}  "
                f"状态已提醒 {run['notified']}  本轮真发 {run['newly_notified']}  "
                f"耗时 {run['elapsed_ms']:.2f} ms"
            )
            for frame in run["frames"]:
                flag = "ERR" if frame["error"] else "OK "
                line = (
                    f"      {flag} {frame['frame_id']:<22} plate={frame['plate'] or '-':<12} "
                    f"rule={frame['rule_hit']} notify={frame['notify_status'] or '-'}"
                )
                log(line + (f"  ← {frame['error']}" if frame["error"] else ""))

        # ---- 阶段 5：沙箱失败 → 重试成功 ---------------------------------
        log("")
        log("=" * 78)
        log("阶段 4：沙箱强制失败 → 重试成功（A07）")
        log("=" * 78)
        fail_pipe = pl.Pipeline(
            session,
            frame_dir=fail_dir,
            bind_map=bind_map_fail,
            sender=notification.SandboxSender(notification.SANDBOX_FAIL),
        )
        # real 识别按 `FRAME_SOURCE_DIR` 找图（与编排同源，见契约 §6.1）——
        # 失败演示换了目录，就必须同时切这个变量，否则识别会去主目录找、找不到。
        os.environ["FRAME_SOURCE_DIR"] = fail_dir
        try:
            fail_run = fail_pipe.run_once(now=JUDGE_NOW)
        finally:
            os.environ["FRAME_SOURCE_DIR"] = frame_dir
        fail_frame = fail_run.frames[0]
        fail_record = fail_frame.record_id
        if fail_record is None:
            log(f"  [!] 失败演示帧未产生记录：error={fail_frame.error}")
        attempts_after_fail = (
            session.get(m.OccupationRecord, fail_record).notify_attempts if fail_record else -1
        )
        log(
            f"  强制失败一轮：record={fail_record} status={fail_frame.notify_status} "
            f"reason={fail_frame.notify_reason} attempts={attempts_after_fail}"
        )
        retry = (
            notification.send_for_record(
                session, fail_record, sender=notification.SandboxSender(notification.SANDBOX_OK)
            )
            if fail_record
            else None
        )
        if retry is not None:
            log(
                f"  重试一次：status={retry.status} attempts={retry.attempts} reason={retry.reason}"
            )

        # ---- 阶段 6：A06 补绑定手机号后重试 -------------------------------
        log("")
        log("=" * 78)
        log("阶段 5：无手机号 → 补绑定后重试成功（A06）")
        log("=" * 78)
        fuel_row = next((r for r in rows if r.scenario == ca.SCENARIO_FUEL), None)
        fuel_before: dict | None = None
        if fuel_row is not None:
            rec = (
                session.query(m.OccupationRecord)
                .filter(m.OccupationRecord.plate == fuel_row.plate)
                .order_by(m.OccupationRecord.id.desc())
                .first()
            )
            fuel_before = {
                "id": rec.id,
                "status": rec.notify_status,
                "attempts": rec.notify_attempts,
                "error": rec.notify_error,
            }
            log(
                f"  燃油记录 id={rec.id} status={rec.notify_status} "
                f"attempts={rec.notify_attempts} reason={rec.notify_error}"
            )
            _register(session, fuel_row.plate, m.VTYPE_FUEL, phone=PHONE)
            again = notification.send_for_record(session, rec.id)
            fuel_after = {"status": again.status, "attempts": again.attempts}
            log(f"  补绑定后重试：status={again.status} attempts={again.attempts}")
        else:
            fuel_after = None

        records = _dump_records(session)

        # ---- 阶段 7：断言 -------------------------------------------------
        log("")
        log("=" * 78)
        log("阶段 6：断言（对应 WEEK3_PLAN §5 验收矩阵）")
        log("=" * 78)
        r1, r2, r3 = rounds
        err_frames = {f["frame_id"]: f for f in r1["frames"] if f["error"]}

        check(
            "A01",
            "自动闭环一轮跑完（取帧→识别→判定→落库→发送）",
            r1["frame_count"] > 0 and r1["violations"] >= 1,
            f"帧 {r1['frame_count']}，违规 {r1['violations']}",
        )
        check(
            "A02", "异常久停命中规则②", any(f["rule_hit"] == m.RULE_ABNORMAL for f in r1["frames"])
        )
        check(
            "A03",
            "充满未移车命中规则③",
            any(f["rule_hit"] == m.RULE_FULL_NOT_MOVED for f in r1["frames"]),
        )
        normal = next((f for f in r1["frames"] if f["frame_id"] == "c_normal.jpg"), None)
        check(
            "A04",
            "正常充电不落库、不发送",
            normal is not None and normal["rule_hit"] is None and normal["record_id"] is None,
            "c_normal.jpg 无违规记录",
        )
        check(
            "A05",
            "第 2 轮不重复发送",
            r2["newly_notified"] == 0,
            f"newly_notified={r2['newly_notified']}",
        )
        check(
            "A06",
            "无手机号不计尝试次数、补绑定后可成功",
            fuel_before is not None
            and fuel_before["attempts"] == 0
            and fuel_before["status"] == m.NOTIFY_FAILED
            and fuel_after is not None
            and fuel_after["status"] == m.NOTIFY_SENT
            and fuel_after["attempts"] == 1,
            f"失败前 attempts={fuel_before['attempts'] if fuel_before else '-'} → 补绑定后 {fuel_after}",
        )
        check(
            "A07",
            "沙箱失败→重试成功；换进程不重发",
            retry is not None
            and retry.status == m.NOTIFY_SENT
            and retry.attempts == attempts_after_fail + 1
            and r3["newly_notified"] == 0,
            f"失败后 attempts={attempts_after_fail} → 重试后 {retry.attempts if retry else '-'}；"
            f"第 3 轮真发 {r3['newly_notified']}",
        )
        check(
            "A09",
            "坏图/无牌失败可见且不伪造结果",
            "z_corrupt.jpg" in err_frames and "z_noplate.jpg" in err_frames,
            "; ".join(f"{k}: {v['error'][:52]}" for k, v in err_frames.items()),
        )
        # A10：逐帧核对「帧 → 车牌 → 桩」。车牌必须帧帧对得上；桩只在**命中违规**的帧上
        # 才有值（规则④ 正常不落库，编排不回填 pile_id），所以正常帧只校车牌。
        mismatch: list[str] = []
        for row in rows:
            if row.is_fail_demo:
                continue
            frame = next((f for f in r1["frames"] if f["frame_id"] == row.dst), None)
            if frame is None or frame["plate"] != row.plate:
                mismatch.append(f"{row.dst}(车牌)")
            elif EXPECTED_RULE[row.scenario] is not None and frame["pile_id"] != row.pile_id:
                mismatch.append(f"{row.dst}(桩)")
        check(
            "A10",
            "帧→车牌→桩 三元组无串帧",
            not mismatch,
            f"不一致：{mismatch}" if mismatch else "逐帧一致",
        )

        failed = [c for c in checks if not c["pass"]]
        log("")
        log(f"结果：{len(checks) - len(failed)}/{len(checks)} 项通过")

        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "real",
            "recognition_weights": os.path.relpath(weights, REPO),
            "frame_source_dir": frame_dir,
            "judge_now": JUDGE_NOW.isoformat(),
            "probe": probe,
            "scenario": [row.to_dict() for row in rows],
            "rounds": rounds,
            "sandbox_fail_recovery": {
                "record_id": fail_record,
                "attempts_after_fail": attempts_after_fail,
                "retry_status": retry.status if retry else None,
                "retry_attempts": retry.attempts if retry else None,
                "retry_reason": retry.reason if retry else None,
            },
            "no_phone_recovery": {"before": fuel_before, "after": fuel_after},
            "records": records,
            "checks": checks,
            "passed": len(checks) - len(failed),
            "total": len(checks),
        }

        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        with open(args.log, "w", encoding="utf-8") as fh:
            fh.write("\n".join(log.lines) + "\n")

        print(
            f"\n凭据已写入：{os.path.relpath(args.json, REPO)} / {os.path.relpath(args.log, REPO)}"
        )
        return 1 if failed else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
