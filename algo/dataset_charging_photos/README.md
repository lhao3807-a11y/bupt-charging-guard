# 网络充电场景实拍图（图片阶段）

2026-10-08 按用户调整后的**网络实拍、先只做图片**口径建立。本目录有 **174 张**经联系表人工筛选的不同 JPEG 照片、逐图来源与许可清单 `manifest.csv`。其中 151 个来源页未出现在原有 `dataset_web`、`dataset_web_supplement` 和 `dataset_scene_mvp` 清单中。图片经最长边 1280px、JPEG quality 88 重编码；清单分别保留源图和入库图 SHA-256。许可字段来自 Openverse，原始来源页可逐图复核；统计为 CC BY 112、CC BY-SA 53、CC0 8、公有领域标记 1。照片中可能有真实车牌，公开演示需另行脱敏。

## 筛选范围与用途

使用 `scripts/collect_charging_photos.py` 从 Openverse 搜索，限定 BY、BY-SA、CC0、公有领域标记，要求作者、来源页与至少 500px 短边。原始候选 405 张下载到忽略目录 `algo/dataset_charging_raw/`；人工看联系表剔除明显无关的汽车、人物、火车、示意图等，并以 dHash 排除两组近重复。入库照片涵盖车辆和充电设备、插枪局部、充电桩、标记车位等**画面可见内容**；并非每张都有车牌或车辆。

2026-10-10 已从本目录选出 97 张并完成人工车辆框/负样本标注，供 M2 微调；标注、划分及生成 YOLO 数据的方法见 [`dataset_vehicle_web`](../dataset_vehicle_web/README.md)。原目录 174 张的来源清单保持采集事实，完整池没有中国车牌号码真值，不参与 M3 OCR 评估。M3 改用来源完整并人工复核的 [`dataset_plate_web`](../dataset_plate_web/README.md) 子集。

单张照片无法证明“空闲久停”“已充满”或占位持续时间。`manifest.csv` 的 `status_evidence=none` 明确记录无充电会话或时间序列证据；不得把本目录按原四类状态各 30 张统计。若后续恢复四类状态验收，需同一桩/车的时序和桩状态记录，再给图片配状态真值。

## 复核

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider algo\tests\test_charging_photo_sources.py algo\tests\test_dataset_charging_photos.py
```

校验覆盖图片数量、来源页唯一、许可白名单、文件 SHA-256 及状态证据标记。许可最终仍须以原始来源页为准，尤其是后续对外再分发时的署名和 BY-SA 条件。
