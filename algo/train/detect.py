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
#: 真实数据集（CCPD 转换产出，任务 5.3）—— 与合成集分开训练，见 algo/tools/ccpd_to_yolo.py
REAL_DATA_YAML = os.path.join(REPO, "algo", "dataset_real", "data.yaml")
BASE_WEIGHTS = os.path.join(REPO, "algo", "weights", "yolov8n.pt")
RUN_DIR = os.path.join(REPO, "algo", "runs", "detect")
# ultralytics 按 name="train" 存产物：algo/runs/detect/train/weights/best.pt
BEST_PT = os.path.join(RUN_DIR, "train", "weights", "best.pt")


def do_train(epochs: int, model: str, data: str = DATA_YAML, name: str = "train") -> int:
    """训练。``data`` / ``name`` 可指定，便于**真实集与合成集分开训**。

    为什么不混在一起训：CCPD 只有车牌框、没有车辆框（见 `ccpd_to_yolo.py` 的说明），
    混进两类的合成集会把 `vehicle` 类教坏。故真实集单独跑一份权重、单独评估。
    """
    from ultralytics import YOLO

    if not os.path.isfile(data):
        print(f"缺少 {data}，请先准备数据集（合成集 gen_synth_dataset.py / 真实集 ccpd_to_yolo.py）")
        return 1

    print(f"== 训练：{model} → {data}，epochs={epochs}，device=0，name={name} ==")
    yolo = YOLO(model)
    yolo.train(
        data=data,
        epochs=epochs,
        device=0,
        project=RUN_DIR,
        name=name,
        exist_ok=True,
        verbose=True,
        # 合成数据集小而规整，适度收敛即可，防止过拟合到噪声
        patience=10,
        batch=16,
        imgsz=640,
    )
    print(f"训练完成，最优权重：{os.path.join(RUN_DIR, name, 'weights', 'best.pt')}")
    return 0


def detect_boxes(image: str, conf: float = 0.5, weights: str | None = None) -> list[dict]:
    """对单张图推理，返回检出框列表 ``[{name, conf, bbox_xywh, bbox_xyxy}]``。

    与 ``do_predict`` 分离，便于单测与 ``algo/recognize`` 复用；
    ``weights`` 缺省用任务 2.3 训练出的 best.pt。
    """
    from ultralytics import YOLO

    src = weights or BEST_PT
    if not os.path.isfile(src):
        raise FileNotFoundError(f"缺少 {src}，请先执行 train 子命令")

    yolo = YOLO(src)
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


def do_predict(image: str, conf: float, weights: str | None = None) -> int:
    import cv2
    from ultralytics import YOLO

    if not os.path.isfile(image):
        print(f"找不到图片：{image}")
        return 1

    used = weights or BEST_PT
    boxes = detect_boxes(image, conf, weights=used)
    print(f"== 推理：{image}（conf>={conf}，权重 {used}）==")
    for b in boxes:
        cx, cy, w, h = b["bbox_xywh"]
        x1, y1, x2, y2 = b["bbox_xyxy"]
        print(
            f"  {b['name']:<8} conf={b['conf']:.3f} "
            f"bbox[x,y,w,h]=[{cx:.0f},{cy:.0f},{w:.0f},{h:.0f}] xyxy=[{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]"
        )

    # 重新推理一次拿可视化结果（保持 detect_boxes 纯净、可复用）
    results = YOLO(used).predict(image, conf=conf, device=0, verbose=False)[0]
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
    p_train.add_argument(
        "--data", default=DATA_YAML, help="数据集 yaml（真实集用 algo/dataset_real/data.yaml）"
    )
    p_train.add_argument(
        "--name", default="train", help="运行名，产物落在 algo/runs/detect/<name>"
    )

    p_pred = sub.add_parser("predict", help="推理验证")
    p_pred.add_argument("--image", help="待推理图片；缺省则取 val 集第一张")
    p_pred.add_argument("--conf", type=float, default=0.5)
    p_pred.add_argument("--weights", default=None, help="权重；缺省用 best.pt")

    args = ap.parse_args()
    if args.cmd == "train":
        return do_train(args.epochs, args.model, args.data, args.name)

    image = args.image
    if image is None:
        cands = sorted(glob.glob(os.path.join(REPO, "algo", "dataset", "images", "val", "*.jpg")))
        if not cands:
            print("val 集为空，请先跑 algo/tools/gen_synth_dataset.py")
            return 1
        image = cands[0]
    return do_predict(image, args.conf, args.weights)


if __name__ == "__main__":
    raise SystemExit(main())
