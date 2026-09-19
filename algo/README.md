# 算法模块（algo/）—— CV 环境与数据说明

负责人：**汤瑾睿**（后端 / DB / 算法）。契约唯一事实源 `docs/CONTRACT.md`，分工排期见 `docs/PLAN_4WEEKS.md`。

---

## 1. CV 环境搭建（PLAN §2.2 任务 2.1）✅ 已完成

**本机实测通过的基线**（2026-09-19）：

| 项 | 版本 / 结果 |
|---|---|
| Python | **3.11.9**（契约 §2 明确勿用 3.13：Ultralytics/PaddleOCR wheels 支持滞后） |
| torch | 2.6.0+cu124 |
| CUDA | 可用 —— NVIDIA GeForce RTX 4060 Laptop GPU（驱动 592.82 / CUDA 13.1） |
| ultralytics | 8.4.155 |
| hyperlpr3 | 0.1.3（onnxruntime 1.30） |
| opencv-python | 5.0.0.93 |

### 从零复现（Windows，GPU 版）

```powershell
# 0) 用 Python 3.11.x 建隔离环境（**不要**装进后端 .venv，避免依赖污染）
& "C:\Users\yy\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv-algo

# 1) 先装 GPU 版 torch —— Windows 上 PyPI 的 torch 是 CPU 版，必须指定官方 cu124 索引
#    （约 2.5GB，本机实测 25 分钟；走代理时先确认 $env:http_proxy 端口，端口会变）
$env:HTTP_PROXY = $env:https_proxy
& ".\.venv-algo\Scripts\python.exe" -m pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision

# 2) 再装其余依赖（走清华源更快）
& ".\.venv-algo\Scripts\python.exe" -m pip install -r algo/requirements-algo.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3) 自检（7 项全 PASS 才算环境搭好）
& ".\.venv-algo\Scripts\python.exe" algo/tools/check_env.py
```

### 踩过的坑

- **C 盘只剩 17GB**：pip 默认缓存/临时目录在 C 盘，装 torch 会吃掉 4GB+。
  装前建议 `$env:TEMP = "E:\tmp"`、`$env:PIP_CACHE_DIR = "E:\tmp\pipcache"`，装完 `pip cache purge`。
- **GitHub release 走代理经常 502**：`YOLO("yolov8n.pt")` 自动下载会失败。
  权重已改由 HF 镜像下载到 `algo/weights/yolov8n.pt`（6.5MB，`.gitignore` 已忽略 `*.pt`），
  `check_env.py` 优先用本地权重。
- **代理端口是动态的**（本次会话先后为 51163 → 56707 → 57456），每次联网前用 `$env:http_proxy` 取当前值。

---

## 2. 目录约定

```
algo/
├── requirements-algo.txt   # CV 依赖（不含 torch，见上文第 1 步）
├── README.md               # 本文件
├── weights/                # 模型权重（*.pt 不入库）
├── tools/
│   ├── check_env.py            # 环境自检（任务 2.1）
│   ├── make_mock_frames.py     # 识别桩占位帧（第 0 天，仅 4 帧）
│   └── gen_synth_dataset.py    # 合成数据集生成（任务 2.2）
├── samples/                # 识别桩样例（frames/*.jpg + labels/*.json，契约 §10）
├── dataset/                # 训练数据集（YOLO 格式，不入库）
└── train/                  # 训练脚本（任务 2.3）
```

---

## 3. 数据集现状（PLAN §2.2 任务 2.2）

- 目标：4 类场景（燃油占位 / 新能源充电中 / 新能源空闲久停 / 已充满），**每类 ≥30 张，合计 ≥120**。
- 当前基线：合成数据集（见 `tools/gen_synth_dataset.py`）+ YOLOv8 官方预训练权重推理。
- ⚠️ **合成图只能验证流程跑通，不能代表真实准确率**。校园实拍替换后需重训（第 2 周）。

---

## 4. 与后端的接口边界

真实 CV 与识别桩 stub 必须返回**同一结构** `RecognitionResult`（契约 §4）：

```json
{ "plate": "京AD12345", "vtype": "新能源", "confidence": 0.97,
  "bbox": [120, 80, 200, 120], "frame_time": "2026-09-08T10:00:00" }
```

`vtype` 由车牌底色判定：**绿牌 = 新能源 / 蓝牌 = 燃油**（契约 §3.1）。
stub / real 的切换开关见 `backend/app/routers/recognize.py`（默认 stub，任务 2.5）。
