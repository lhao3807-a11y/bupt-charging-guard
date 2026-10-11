"""自动闭环编排进程（契约 v1.9 §6.11 / 第 3 周 T3）。

把「取帧 → 识别 → 判定 → 落库 → 沙箱发送」串起来，**这是唯一的自动入口**。
识别模式跟随 `RECOGNITION_MODE`（real = 真跑 CV，stub = 读标注），
与 `/api/recognize` 复用同一套实现，不另写一份。

用法（仓库根目录）：

```powershell
.venv\\Scripts\\python.exe scripts\\run_pipeline.py                      # 跑一轮
.venv\\Scripts\\python.exe scripts\\run_pipeline.py --loop --interval 5   # 每 5 秒一轮
.venv\\Scripts\\python.exe scripts\\run_pipeline.py --at 2026-09-08T10:00:00   # 固定时刻（可复现）
.venv\\Scripts\\python.exe scripts\\run_pipeline.py --bind-map 003.jpg=PILE-003,004.jpg=PILE-002
.venv\\Scripts\\python.exe scripts\\run_pipeline.py --sandbox-fail        # 演示「发送失败」
.venv\\Scripts\\python.exe scripts\\run_pipeline.py --timing 5            # 耗时采样（T7 性能凭据）
```

**与前端的关系**：本进程把每轮结果写到状态文件，`GET /api/pipeline/status`
只读该文件。刷新页面**不会**触发识别或发送（避免「刷新即发短信」）。

⚠️ 会写当前 `DATABASE_URL` 指向的库（落库 + 更新提醒状态），演示请用独立库。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
REPO = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import models as m
from app import pipeline as pl
from app.db import SessionLocal, engine
from app.notification import SANDBOX_FAIL, SANDBOX_RESULT_ENV

_RULE_LABELS = {1: "①燃油占位", 2: "②异常占位", 3: "③充满未移车"}


def _parse_bind_map(raw: str | None) -> dict[str, str]:
    """`003.jpg=PILE-003,004.jpg=PILE-002` → dict；也支持传一个 JSON 文件路径。"""
    if not raw:
        return {}
    if os.path.isfile(raw):
        with open(raw, encoding="utf-8") as fh:
            return {str(k): str(v) for k, v in json.load(fh).items()}
    mapping: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"--bind-map 格式应为 帧名=桩ID，收到：{item!r}")
        frame, pile_id = item.split("=", 1)
        mapping[frame.strip()] = pile_id.strip()
    return mapping


def _print_run(run: pl.PipelineRun) -> None:
    print(f"\n=== 编排一轮 {run.started_at.isoformat()} ===")
    print(f"帧目录：{run.frame_count} 张　识别 {run.recognized}　复用 {run.skipped_unchanged}")
    for frame in run.frames:
        if frame.error:
            print(f"  [ERROR] {frame.frame_id}：{frame.error}")
            continue
        if frame.rule_hit:
            print(
                f"  [违规] {frame.frame_id}　{frame.plate}　{frame.pile_id}　"
                f"{_RULE_LABELS.get(frame.rule_hit, frame.rule_hit)}　"
                f"记录#{frame.record_id}　提醒={frame.notify_status}"
                + (f"（{frame.notify_reason}）" if frame.notify_reason else "")
            )
        else:
            extra = "（复用识别结果）" if frame.reused else ""
            print(f"  [正常] {frame.frame_id}　{frame.plate}　未违规{extra}")
    # 「已提醒」是状态，「本轮新发」才是动作 —— 自动轮询下两者经常不等，别混着报
    print(f"  小计：违规 {run.violations}　已提醒 {run.notified}（本轮新发 {run.newly_notified}）")


def _stats(samples: list[float]) -> dict:
    """一组耗时的 min/max/均值/中位数（毫秒，两位小数）。"""
    ordered = sorted(samples)
    n = len(ordered)
    return {
        "count": n,
        "min_ms": round(ordered[0], 2),
        "max_ms": round(ordered[-1], 2),
        "mean_ms": round(sum(ordered) / n, 2),
        "p50_ms": round(ordered[(n - 1) // 2], 2),
    }


def _default_timing_path() -> str:
    return os.path.join(REPO, "docs", "acceptance", "week3", "04-timing-sample.json")


def _run_timing(worker: pl.Pipeline, rounds: int, out: str | None, fixed_now) -> int:
    """耗时采样：连跑 N 轮，统计整轮与逐帧耗时（第 3 周 T7 的性能凭据）。

    刻意**连跑多轮**而不是只跑一轮：第 2 轮起会复用识别结果（内容未变），
    两组数字摆在一起才能说明「复用到底省了多少」，而不是拍脑袋说「很快」。
    """
    target = out or _default_timing_path()
    samples = []
    for i in range(1, rounds + 1):
        run = worker.run_once(now=fixed_now)
        samples.append(run)
        print(
            f"  第 {i:>2} 轮：{run.elapsed_ms:>8.2f} ms　"
            f"识别 {run.recognized}/{run.frame_count}　复用 {run.skipped_unchanged}　"
            f"违规 {run.violations}　已提醒 {run.notified}（本轮新发 {run.newly_notified}）"
        )

    per_frame: dict[str, list[float]] = {}
    for run in samples:
        for frame in run.frames:
            if frame.elapsed_ms is not None:
                per_frame.setdefault(frame.frame_id, []).append(frame.elapsed_ms)

    payload = {
        "sampled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": rounds,
        "frame_count": samples[0].frame_count if samples else 0,
        "recognition_mode": os.environ.get("RECOGNITION_MODE", "stub"),
        "round_elapsed_ms": _stats([r.elapsed_ms for r in samples if r.elapsed_ms is not None]),
        "per_frame_elapsed_ms": {k: _stats(v) for k, v in sorted(per_frame.items())},
        "detail": [
            {
                "round": i,
                "elapsed_ms": r.elapsed_ms,
                "recognized": r.recognized,
                "reused": r.skipped_unchanged,
                "violations": r.violations,
                "notified": r.notified,
                "newly_notified": r.newly_notified,
                "frames": [
                    {
                        "frame_id": f.frame_id,
                        "elapsed_ms": f.elapsed_ms,
                        "reused": f.reused,
                        "rule_hit": f.rule_hit,
                    }
                    for f in r.frames
                ],
            }
            for i, r in enumerate(samples, start=1)
        ],
    }

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"  耗时采样已写入：{target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="自动闭环编排进程（识别→判定→落库→沙箱提醒）")
    parser.add_argument("--loop", action="store_true", help="循环运行（默认每 10 秒一轮）")
    parser.add_argument("--interval", type=float, default=10.0, help="循环间隔秒数")
    parser.add_argument("--times", type=int, default=0, help="循环轮数，0 = 不限")
    parser.add_argument("--at", default=None, help="把「现在」设为该时刻（ISO 8601），便于复现")
    parser.add_argument("--frames", default=None, help="取帧目录，默认 algo/samples/frames")
    parser.add_argument("--status-file", default=None, help="状态文件写入路径")
    parser.add_argument(
        "--bind-map", default=None, help="帧→桩映射（`003.jpg=PILE-003,...` 或 JSON 文件）"
    )
    parser.add_argument(
        "--sandbox-fail",
        action="store_true",
        help="把沙箱发送器置为恒失败（演示失败与恢复，等价 SMS_SANDBOX_RESULT=fail）",
    )
    parser.add_argument(
        "--timing",
        type=int,
        default=0,
        metavar="N",
        help="耗时采样：连跑 N 轮并统计整轮/逐帧耗时（T7 性能凭据），0 = 不采样",
    )
    parser.add_argument("--timing-out", default=None, help="耗时采样 JSON 的写入路径")
    args = parser.parse_args()

    if args.sandbox_fail:
        os.environ[SANDBOX_RESULT_ENV] = SANDBOX_FAIL

    fixed_now = datetime.fromisoformat(args.at) if args.at else None
    bind_map = _parse_bind_map(args.bind_map)

    m.init_db(engine)
    db = SessionLocal()
    m.seed_db(db)
    worker = pl.Pipeline(db, frame_dir=args.frames, bind_map=bind_map)

    try:
        if args.timing:
            return _run_timing(worker, args.timing, args.timing_out, fixed_now)

        rounds = 0
        while True:
            run = worker.run_once(now=fixed_now)
            _print_run(run)
            target = pl.write_status(run, args.status_file)
            print(f"  状态文件：{target}")

            rounds += 1
            if not args.loop:
                break
            if args.times and rounds >= args.times:
                break
            # 循环模式下按真实节奏推进：--at 只用于首轮复现，之后交给系统时钟
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
