# CV 产物凭据（第 2 周任务 5.1）

> **为什么会有这个目录**：第 1 周审查留下的**唯一真风险**是「CV 产物没有仓库内凭据」——
> `algo/dataset` 与 `algo/runs` 都被 `.gitignore` 忽略，本机也不存在，
> 于是「数据集生成 / 训练 / 推理」这三件事**无法证明真的跑过**（第 1 周 R1）。
> 本目录把复跑的**日志与截图**存进仓库，让 M1–M3 可以从仓库里直接验收。

**复跑时间** 2026-10-05　**执行人** 汤瑾睿　**机器** NVIDIA GeForce RTX 4060 Laptop GPU（CUDA 可用）

## 一、复跑步骤（可复现）

在仓库根目录执行（用算法环境 `.venv-algo`，不是后端 `.venv`）：

```bat
.venv-algo\Scripts\python.exe algo\tools\check_env.py           > docs\acceptance\algo\00-check-env.log 2>&1
.venv-algo\Scripts\python.exe algo\tools\gen_synth_dataset.py   > docs\acceptance\algo\01-gen-dataset.log 2>&1
.venv-algo\Scripts\python.exe algo\train\detect.py train --epochs 40 > docs\acceptance\algo\02-train.log 2>&1
.venv-algo\Scripts\python.exe algo\train\detect.py predict       > docs\acceptance\algo\03-predict.log 2>&1
```

> ⚠️ **踩坑**：`train` 会去 GitHub 下载预训练权重 `yolov8n.pt`（约 6.5 MB），
> 本机代理下 ultralytics 的下载器会 `502` 失败（日志里能看到 3 次重试）。
> 解决办法是**先用系统代理把权重下到 `algo/weights/yolov8n.pt`**（该目录已被忽略，不入库）：
> ```powershell
> Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt" `
>   -Proxy "http://127.0.0.1:7897" -OutFile "algo\weights\yolov8n.pt"
> ```
> 有本地权重后 `YOLO(...)` 不会再触发联网下载。

## 二、结果

| 环节 | 证据 | 结论 |
|---|---|---|
| 环境自检 | `00-check-env.log` | **7/7 PASS**：Python 3.11.9 / torch 2.6.0+cu124 / CUDA 可用（RTX 4060）/ ultralytics 8.4.155 / hyperlpr3 0.1.3 |
| 数据集生成 | `01-gen-dataset.log` | 132 张（train 109 / val 23），2 类 `vehicle` / `plate` |
| 训练 | `02-train.log`、`results.png` | 40 epoch 预算、epoch 27 早停，**mAP50 = 0.995 / mAP50-95 = 0.995**，P=0.997 R=1.0 |
| 推理验证 | `03-predict.log`、`charging_006_pred.jpg` | val 集 `charging_006.jpg` 同时检出车辆（conf 0.973）与车牌（conf 0.923），框位正确 |

![训练曲线](results.png)

![推理可视化](charging_006_pred.jpg)

## 三、⚠️ 这些指标**不能**当作真实准确率

训练与验证用的是**合成数据集**（`algo/tools/gen_synth_dataset.py` 生成的 4 类场景：
燃油占位 / 新能源空闲久停 / 充电中 / 已充满），不是校园实拍。

- 合成帧上的 mAP50 = 0.995 只说明「**流程跑通了**」——数据生成 → 标注 → 训练 → 推理 → 输出
  `RecognitionResult` 结构，这条链路是通的。
- **S3 的准确率指标必须等校园实拍集到位后重训再评估**（第 2 周任务 5.3–5.5），
  届时本报告会补「实拍 val 集 mAP50」一栏，替换掉这个数字。

## 四、产物位置（均不入库，`.gitignore` 已忽略）

| 产物 | 路径 |
|---|---|
| 合成数据集 | `algo/dataset/`（images / labels / data.yaml / meta.json） |
| 训练权重 | `algo/runs/detect/train/weights/best.pt`（6.2 MB） |
| 预训练权重 | `algo/weights/yolov8n.pt`（6.5 MB，需自行下载，见上文踩坑） |
