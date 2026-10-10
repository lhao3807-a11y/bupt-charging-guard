# M2/M3 网络实拍验收（2026-10-10）

按用户批准的两模型方案交付：网络充电照片用于车辆检测，来源完整的中国车牌照片用于车牌检测、OCR 和绿蓝牌车型判定。用户未设准确率门槛，要求报告真实指标；充电会话与时间状态证据暂缓。本页是新网络图片口径的验收记录，旧校园四状态快照保留历史含义。

## 数据与训练

| 模型 | 训练/验证 | 标注与划分 | 实际训练 |
|---|---|---|---|
| vehicle | 80 / 17 张 | 97 张充电实拍，62 个手工车辆框、50 张负样本；val 为 9 张有目标/8 张负样本、14 个框 | YOLOv8n 官方预训练权重微调，640px、batch 8、freeze 10、seed 42、CPU；40 epoch，不早停 |
| plate | 75 / 18 张 | 93 张来源完整的中国普通蓝/绿牌；人工重看 94 张号码裁剪，排除 1 张警用牌、修正 11 张号码 | 同一官方预训练基线，640px、batch 8、freeze 10、seed 42、CPU；计划 40 epoch、patience 10，实际早停于 28 epoch |

两个数据集均按摄影作者分组，同一作者不跨 train/val；号牌亦无跨划分重复。图像/来源/框/号码/车型/哈希清单见 [`dataset_vehicle_web`](../../../../algo/dataset_vehicle_web/README.md)、[`dataset_plate_web`](../../../../algo/dataset_plate_web/README.md)。不使用缺来源的 80 张旧网络图、合成图或缺失的本地 CCPD 数据。完整依赖与 OCR 模型校验值见 [`environment.json`](environment.json)，训练参数、逐 epoch CSV 和清理后的训练日志均在本目录。

车辆标注只覆盖可见车身框面积至少为画面 5% 的轿车/厢式车，可包含部分出画和遮挡。远处小车辆不属于本次标注目标。复审另记两处小车忽略区域，业务阈值统计会将与这些区域 IoU≥0.5 的预测单列。原始 Ultralytics mAP 不支持本清单的忽略区域，仍会惩罚这些范围外的正确小车检出，故该原始指标有保守偏差；不能据此解释为全部框均为真实误检。

## 独立 val 结果

| 检测器 | mAP50 | mAP50–95 | 阈值 0.4、IoU≥0.5 的检出统计 |
|---|---|---|---|
| vehicle | **0.8341** | **0.5692** | TP 12、FP 3、FN 2、忽略范围外小车 1；precision 80.00%、recall 85.71% |
| plate | **0.9867** | **0.8390** | TP 16、FP 1、FN 2；precision 94.12%、recall 88.89% |

[`vehicle-detection.json`](vehicle-detection.json) / [`plate-detection.json`](plate-detection.json) 包含权重和清单 SHA-256、样本数、原始 Ultralytics 指标及阈值 0.4 的逐图预测。清单使用 canonical JSON（UTF-8、排序键、紧凑序列化）计算哈希，避免 Git 的 CRLF/LF 差异；权重和图片采用文件字节哈希。原始库输出的 precision/recall 使用其自身阈值汇总，与表中固定业务阈值的统计不同。验证集合较小、已用于常规模型选优，未另设最终测试集；这些数字仅代表该原型 val，不能外推校园全天候或生产准确率。

M3 使用 `recognize_frame()` 的默认真实权重，在全部 18 张 val 上调用实际检测 → 整帧 OCR 对应框匹配 → 车型判定，并用生产 `RecognitionResult` 校验每个输出。使用检测框，不使用 GT 框辅助 OCR。

| 识别项 | 结果 |
|---|---|
| 检出并产生合法结构 | 16 / 18；16 个结果通过 Pydantic 契约校验 |
| 检出后的 OCR 整串准确率 | **15 / 16 = 93.75%** |
| 全 val 端到端 OCR 整串准确率 | **15 / 18 = 83.33%**（漏检和空号码都计失败） |
| 检出后的车型准确率 | **16 / 16 = 100%** |
| 全 val 车型正确率 | **16 / 18 = 88.89%** |
| 全 val 号码和车型同时正确 | **15 / 18 = 83.33%** |

逐图输出和失败记录见 [`recognition.json`](recognition.json)。`web_0694.jpg` 检出后 OCR 空串，`web_0696.jpg` 和 `web_0718.jpg` 在 0.4 阈值下漏检；这三张保留在分母中。另用真实照片经生产 `/api/recognize` 路由完成 HTTP 测试，验证真实模式返回 200、正确号码和车型、合规结构，无数据库写入。车型是契约约定的绿/蓝牌映射，不是对所有车辆动力类型的独立识别模型。

## 权重与调用

模型文件依项目约定保留在忽略目录、当前本机可用；Git 保存代码、标注、来源清单、训练日志及指标，复现时重新训练。两个 `best.pt` 均为约 6MB，校验值已记录在对应检测 JSON 中。

- M2：`algo/runs/detect/train_vehicle_web/weights/best.pt`；Python 入口 `algo.train.detect.detect_vehicles(image_path)`。
- M3：`algo/runs/detect/train_plate_web/weights/best.pt`；这是 `algo.recognize.plate.DEFAULT_WEIGHTS` 的当前值，生产 real 模式使用它。
- `recognize_frame()` 支持 Windows 中文路径、复用 OCR 模型实例；OCR 框与目标检测框没有重叠时返回空号码，避免读到别车的牌。

## 从仓库根目录复现

```powershell
# 独立环境；本次使用 CPU，CUDA 不是复现前提。
.venv/Scripts/python.exe -m venv .venv-algo
.venv-algo/Scripts/python.exe -m pip install torch==2.6.0 torchvision==0.21.0
.venv-algo/Scripts/python.exe -m pip install -r algo/requirements-algo.txt pytest ruff

New-Item -ItemType Directory -Force .tmp-m2/ultralytics/Ultralytics | Out-Null
$env:YOLO_CONFIG_DIR = Join-Path (Get-Location) '.tmp-m2/ultralytics'
$env:OMP_NUM_THREADS = '4'
$env:PYTHONUTF8 = '1'

# 下载官方 YOLOv8n 预训练权重，复制到训练默认位置。
.venv-algo/Scripts/python.exe -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
New-Item -ItemType Directory -Force algo/weights | Out-Null
Copy-Item -LiteralPath yolov8n.pt -Destination algo/weights/yolov8n.pt

# HyperLPR3 首次导入会下载自己的模型到用户缓存。
.venv-algo/Scripts/python.exe -c "import hyperlpr3"

.venv-algo/Scripts/python.exe algo/tools/prepare_week2.py
.venv-algo/Scripts/python.exe algo/train/detect.py train --data .tmp-m2/data/vehicle/data.yaml --name train_vehicle_web --device cpu --epochs 40 --imgsz 640 --batch 8 --freeze 10 --patience 0
.venv-algo/Scripts/python.exe algo/train/detect.py train --data .tmp-m2/data/plate/data.yaml --name train_plate_web --device cpu --epochs 40 --imgsz 640 --batch 8 --freeze 10
.venv-algo/Scripts/python.exe algo/tools/verify_week2.py vehicle
.venv-algo/Scripts/python.exe algo/tools/verify_week2.py plate
.venv-algo/Scripts/python.exe algo/tools/verify_week2.py recognition
.venv-algo/Scripts/python.exe algo/train/detect.py predict --weights algo/runs/detect/train_vehicle_web/weights/best.pt --image algo/dataset_charging_photos/images/charging_0017.jpg --conf 0.4

# 旧合成集测试需要其数据；它不会进入上述真实训练。
.venv-algo/Scripts/python.exe algo/tools/gen_synth_dataset.py
.venv-algo/Scripts/python.exe -m pytest algo/tests -q -p no:cacheprovider
```

本机首次 HyperLPR3 导入在解压完成、删除 ZIP 时遇到 Windows `WinError 32`；再次运行同一导入命令成功，模型校验值见环境记录。Polars 固定 1.35.2，避免本机 2.0.0 的 `unknown feature flag: sse3` 错误。Windows 沙箱中的 HTTP TestClient 曾停滞，最终在获准的本机环境、隔离内存 SQLite 下完成相关验证。

## 验证画面与来源

最终回归：算法 **66 passed / 4 skipped**（跳过的是缺旧合成模型权重的用例，新实拍、真实 API、数据与凭据检查均执行）；后端 **253 passed**；Ruff、修改文件格式检查和依赖一致性检查通过。日志保存在本目录。独立代码复审检查了划分、指标分母、默认权重、中文路径和契约输出；提出的小车范围统计问题已修复并复审通过。

[`vehicle-validation.jpg`](vehicle-validation.jpg) 覆盖全部车辆 val：绿框为标注、红框为预测、橙框为忽略区域，图注列 TP/FP/FN/I；范围外小车单列为 ignored。[`plate-validation.jpg`](plate-validation.jpg) 展示全部号牌 val 的真值裁剪与预测号码，红字为失败。图片只用于核对，所有算法输入均为完整原图。

照片作者和原始来源页逐图保留在对应 manifest；这些裁剪/画框预览沿用各源图 CC BY / CC BY-SA / CC0 条件。技术依据：[Ultralytics 训练](https://docs.ultralytics.com/modes/train/)、[检测数据格式](https://docs.ultralytics.com/datasets/detect/)、[HyperLPR 官方仓库](https://github.com/szad670401/HyperLPR)。
