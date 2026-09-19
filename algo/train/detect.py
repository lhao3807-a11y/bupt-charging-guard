"""YOLOv8 车辆/车牌检测：训练 + 推理验证（PLAN §2.2 任务 2.3）。

流程
----
1. ``train``：从 ``algo/dataset/data.yaml`` 读合成数据集，在预训练 ``yolov8n.pt``
   基础上微调（GPU 设备 0），产出 ``algo/runs/detect/weights/best.pt``。
2. ``predict``：用 best.pt 对指定图推理，把检出框存为 ``*_pred.jpg`` 并打印
   ``cls xywh``（车辆/车牌检测的验收：能框出车牌与车辆区域、输出 bbox）。

用法（在仓库根目录）::

    # 训练（4060 上 132 张 × 40 epoch 约几分钟）
    .venv-algo\\Scripts\\python.exe algo/train/detect.py train --epochs 40

    # 推理验证（默认抽 val 集第 1 张）
    .venv-algo\\Scripts\\python.exe algo/train/detect.py predict --image algo/dataset/images/val/xxx.jpg

说明
----
- 权重与训练产物均不入库（``.gitignore`` 已忽略 ``*.pt`` 与 ``algo/runs/``）。
- 合成数据训练出的模型**只在合成帧上有效**，实拍替换后需重训（algo/README.md §3）。
"""

from __future__ import annotations

import argparse
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA_YAML = os.path.join(REPO, "algo", "dataset", "data.yaml")
BASE_WEIGHTS = os.path.join(REPO, "algo", "weights", "yolov8n.pt")
RUN_DIR = os.path.join(REPO, "algo", "runs", "detect")
# ultralytics 按 name="train" 存产物：algo/runs/detect/train/weights/best.pt
BEST_PT = os.path.join(RUN_DIR, "train", "weights", "best.pt")


def do_train(epochs: int, model: str) -> int:
    from ultralytics import YOLO

    if not os.path.isfile(DATA_YAML):
        print(f"缺少 {DATA_YAML}，请先跑 algo/tools/gen_synth_dataset.py")
        return 1

    print(f"== 训练：{model} → {DATA_YAML}，epochs={epochs}，device=0 ==")
    yolo = YOLO(model)
    yolo.train(
        data=DATA_YAML,
        epochs=epochs,
        device=0,
        project=RUN_DIR,
        name="train",
        exist_ok=True,
        verbose=True,
        # 合成数据集小而规整，适度收敛即可，防止过拟合到噪声
        patience=10,
        batch=16,
        imgsz=640,
    )
    print(f"训练完成，最优权重：{BEST_PT}")
    return 0


def detect_boxes(image: str, conf: float = 0.5) -> list[dict]:
    """对单张图推理，返回检出框列表 ``[{name, conf, bbox_xywh, bbox_xyxy}]``。

    与 ``do_predict`` 分离，便于单测与后续 ``algo/recognize`` 复用。
    """
    from ultralytics import YOLO

    if not os.path.isfile(BEST_PT):
        raise FileNotFoundError(f"缺少 {BEST_PT}，请先执行 train 子命令")

    yolo = YOLO(BEST_PT)
    results = yolo.predict(image, conf=conf, device=0, verbose=False)[0]
    names = results.names
    out: list[dict] = []
    for box in results.boxes:
        xyxy = [float(v) for v in box.xyxy[0].tolist()]
        cx, cy, w, h = (float(v) for v in box.xywh[0].tolist())
        out.append(
            {
                "name": names[int(box.cls)],
                "conf": float(box.conf),
                "bbox_xywh": [cx, cy, w, h],
                "bbox_xyxy": xyxy,
            }
        )
    return out


def do_predict(image: str, conf: float) -> int:
    import cv2
    from ultralytics import YOLO

    if not os.path.isfile(image):
        print(f"找不到图片：{image}")
        return 1

    boxes = detect_boxes(image, conf)
    print(f"== 推理：{image}（conf>={conf}）==")
    for b in boxes:
        cx, cy, w, h = b["bbox_xywh"]
        x1, y1, x2, y2 = b["bbox_xyxy"]
        print(
            f"  {b['name']:<8} conf={b['conf']:.3f} "
            f"bbox[x,y,w,h]=[{cx:.0f},{cy:.0f},{w:.0f},{h:.0f}] xyxy=[{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]"
        )

    # 重新推理一次拿可视化结果（保持 detect_boxes 纯净、可复用）
    results = YOLO(BEST_PT).predict(image, conf=conf, device=0, verbose=False)[0]
    annotated = results.plot()  # BGR
    out = os.path.splitext(os.path.basename(image))[0] + "_pred.jpg"
    out_path = os.path.join(RUN_DIR, out)
    cv2.imwrite(out_path, annotated)
    print(f"可视化已保存：{out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="YOLOv8 车辆/车牌检测（任务 2.3）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_train = sub.add_parser("train", help="训练")
    p_train.add_argument("--epochs", type=int, default=40)
    p_train.add_argument("--model", default=BASE_WEIGHTS, help="预训练权重（默认 yolov8n）")

    p_pred = sub.add_parser("predict", help="推理验证")
    p_pred.add_argument("--image", help="待推理图片；缺省则取 val 集第一张")
    p_pred.add_argument("--conf", type=float, default=0.5)

    args = ap.parse_args()
    if args.cmd == "train":
        return do_train(args.epochs, args.model)

    image = args.image
    if image is None:
        cands = sorted(glob.glob(os.path.join(REPO, "algo", "dataset", "images", "val", "*.jpg")))
        if not cands:
            print("val 集为空，请先跑 algo/tools/gen_synth_dataset.py")
            return 1
        image = cands[0]
    return do_predict(image, args.conf)


if __name__ == "__main__":
    raise SystemExit(main())
