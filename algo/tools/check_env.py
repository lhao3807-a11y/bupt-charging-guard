"""CV 环境自检脚本（任务 2.1 的验收凭据）。

用途
----
在 ``.venv-algo`` 里跑一遍，确认：Python 版本、torch + CUDA、YOLOv8 推理、
HyperLPR3 车牌识别全部可用。**任何一项 FAIL 都不算环境搭好**。

用法：``.venv-algo\\Scripts\\python.exe algo/tools/check_env.py``
（可选参数 ``--frame algo/samples/frames/001.jpg`` 指定自检用图）

说明：本脚本**不训练**，只做「能不能跑起来」的冒烟测试；
真正的数据集与训练脚本见 ``algo/tools/gen_synth_dataset.py`` 与 ``algo/train/detect.py``。
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_FRAME = os.path.join(REPO, "algo", "samples", "frames", "001.jpg")
# 本地权重优先：GitHub release 走代理经常 502，权重改由镜像站下载后放这里
DEFAULT_WEIGHTS = os.path.join(REPO, "algo", "weights", "yolov8n.pt")

# 契约 §2 基线：Python 3.11.x（勿用 3.13，Ultralytics/PaddleOCR wheels 支持滞后）
REQUIRED_PY = (3, 11)

checks: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def check_python() -> None:
    v = sys.version_info
    ok = (v.major, v.minor) == REQUIRED_PY
    record(
        "python 版本",
        ok,
        f"{v.major}.{v.minor}.{v.micro}（要求 {REQUIRED_PY[0]}.{REQUIRED_PY[1]}.x）",
    )


def check_torch() -> bool:
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        record("torch 导入", False, str(exc))
        return False

    record("torch 导入", True, torch.__version__)
    cuda = torch.cuda.is_available()
    record("CUDA 可用", cuda, torch.cuda.get_device_name(0) if cuda else "无 GPU / 驱动不匹配")
    return True


def check_yolo(frame: str, weights: str):
    """YOLOv8 推理冒烟：用官方预训练权重跑一帧，只要能出 boxes 即可。"""
    try:
        from ultralytics import YOLO
    except Exception as exc:  # noqa: BLE001
        record("ultralytics 导入", False, str(exc))
        return

    import ultralytics

    record("ultralytics 导入", True, f"v{ultralytics.__version__}")

    src = weights if os.path.isfile(weights) else "yolov8n.pt"
    try:
        model = YOLO(src)  # 本地权重缺失时会自动下载 ~6MB
        results = model.predict(frame, verbose=False, device=0)
        boxes = results[0].boxes
        n = 0 if boxes is None else len(boxes)
        cls = []
        if boxes is not None and n:
            cls = [model.names[int(c)] for c in boxes.cls.tolist()]
        record("YOLOv8 推理", True, f"{os.path.basename(src)} → {frame} 检出 {n} 个框 {cls}")
    except Exception as exc:  # noqa: BLE001
        record("YOLOv8 推理", False, str(exc))


def check_hyperlpr(frame: str):
    """车牌识别冒烟：本图是合成帧，识别不出车牌也算通过（只验证库能跑）。"""
    try:
        import hyperlpr3 as lpr3
    except Exception as exc:  # noqa: BLE001
        record("hyperlpr3 导入", False, str(exc))
        return

    record("hyperlpr3 导入", True, getattr(lpr3, "__version__", "0.1.3"))

    try:
        import cv2

        img = cv2.imread(frame)
        if img is None:
            record("HyperLPR3 推理", False, f"读不到图片：{frame}")
            return

        catcher = lpr3.LicensePlateCatcher()
        res = catcher(img)
        record("HyperLPR3 推理", True, f"返回 {len(res)} 条结果（合成帧可能为 0，属正常）")
    except Exception as exc:  # noqa: BLE001
        record("HyperLPR3 推理", False, str(exc))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", default=DEFAULT_FRAME, help="自检用图片路径")
    ap.add_argument(
        "--weights", default=DEFAULT_WEIGHTS, help="YOLO 权重路径（默认 algo/weights/yolov8n.pt）"
    )
    args = ap.parse_args()

    print("=== CV 环境自检（任务 2.1）===")
    check_python()
    if check_torch():
        check_yolo(args.frame, args.weights)
        check_hyperlpr(args.frame)

    failed = [n for n, ok, _ in checks if not ok]
    print("-" * 40)
    print(f"合计 {len(checks)} 项，失败 {len(failed)} 项")
    if failed:
        print("失败项：" + "、".join(failed))
        return 1
    print("环境 OK ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
