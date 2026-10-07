# 网络素材场景 MVP（冒烟验证用）

本目录把现有网络素材整理成可追溯、可验证的演示数据，用于先跑通场景展示/规则链路。**它不是四类校园照片标注集，也不得用于模型训练或准确率评估。**

## 内容

- 共登记 **109 张不同图片**：复用 [`dataset_web_supplement`](../dataset_web_supplement/) 中已有 80 张，并新增本目录 `images/` 下 29 张经过人工快速目视检查的公开授权图片。
- [`licenses.csv`](licenses.csv) 为 109 张图片统一登记本地路径、标题、作者、原始来源页、原图 URL、许可、许可版本和 SHA-256。复用时按对应来源页及许可要求署名；CC BY-SA 素材的再分发须遵守相同方式共享要求。
- [`scene_cases.json`](scene_cases.json) 提供四类各 30 条、每类内部不重复图片的**演示事件样例**。跨类别可以复用同一张照片；总计 120 条不等于 120 张独立校园照片。
- 所有样例都标记 `status_origin=synthetic_demo`、`training_eligible=false`。燃油/新能源类型、是否正在充电、停留时长、是否充满均不能仅凭静态照片推断；相关事件状态仅用于验证程序链路。

## 校园场景与验收边界

素材主要是一般道路、停车和充电站照片，不是本校实拍。只有少量来源标题提到大学校园（例如 TU/e、CCU），仍未核验为本项目要求的校园实拍。清单中的 `campus_verified` 当前全部为 `false`。

所以本 MVP 可用于检查四类演示事件能否被读入、展示和走完规则流程；它**没有**完成原定“校园四类场景各至少 30 张”的 M1 数据验收，也不能代替实拍验证、人工框标注、训练/验证划分或模型评估。严格验收状态仍以 [`docs/WEEK2_ACCEPTANCE.md`](../../docs/WEEK2_ACCEPTANCE.md) 为准。

## 数据来源

- 图片发现与许可元数据：[Openverse API](https://api.openverse.org/v1/)。Openverse 是素材发现入口；每张图片的许可/署名以清单记录的原始来源页为准。
- 新增照片仅保留 `CC BY`、`CC BY-SA`、`CC0` 或公有领域许可项；不纳入 `NC`/`ND` 限制项。
- 静态图无法证明“久停”或“充满后未移车”。相关真实状态需要跨时间帧、充电桩状态和车辆绑定记录。

## 校验

在仓库根目录运行：

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider algo\tests\test_dataset_scene_mvp.py -q
```

测试检查四类各 30 条、单类图片不重复、每张图片可定位、许可/来源字段完整、SHA-256 一致，以及场景状态全部被排除在训练数据之外。
