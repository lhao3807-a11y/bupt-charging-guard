# 返工清单逐条对账（汤瑾睿）

> 对账日期：2026-10-13　被对账文档：`TANG_WEEK3_REWORK.md`（核查日期 2026-10-13）
> 对账基线：`feature/api-week3`
> **对账原则**：每条都用仓库内的可复现证据回答，不用「已经做了」这种说法；
> 核查方判断与仓库实况不符的，直接给出反例命令与输出。

## 0. 一句话结论

清单里的 **T1–T7 主要实现全部在位**，本轮（10-13）补齐了清单点名的三类缺失：
**① real 模式端到端凭据（A09/A10）　② 专项测试复跑凭据（A16）　③ 验收矩阵回填与签认表（A13）**。
另有 **3 处核查判断与仓库实况不符**（见 §1），其中 2 处是核查时点/方式问题、1 处属实。

## 1. 对核查结论中三处事实的更正

### ① 「远端分支没有 `docs/acceptance/week3/`」——**不成立**

```bash
git ls-tree -r --name-only origin/feature/api-week3 -- docs/acceptance/week3
# 01-verify-mysql-v19.json   01-verify-mysql-v19.log   02-seed-demo.log
# 03-pipeline-mysql.json     03-pipeline-mysql.log
# 04-timing-sample.json      04-timing-sample.log
```

该目录自第 3 周 T7 提交（`b33da9c`）起就在远程。核查方看到的可能是**更早的时点**
（那批凭据的推送与核查时间的先后关系无法从仓库复原）。本轮又新增了 `05–08` 四份，一并附上。

### ② 「现有 `backend/app/routers/notify.py` 仍是旧接口：调用方传入 `id` 和 `notify_status` 后直接更新记录」——**不成立**

`notify.py` 已在 v1.9 重写（T2，提交 `357540a`）。当前入参是「记录 ID + `retry` 意图」，
`notify_status` **不再由调用方指定**，而由沙箱执行结果产生：

```bash
git show origin/feature/api-week3:backend/app/routers/notify.py | head -40
```

清单描述的「传入 `notify_status` 就写库」是 **v1.2 行为**，对应 `rule_engine.mark_notified()`
（该函数为兼容保留，已不在 `/api/notify` 路径上）。

### ③ 「分支相对当时远端 `main` 为 ahead 34 / behind 12」——**数字已过期**

| 时点 | behind（main 独有） | ahead（分支独有） |
|---|---|---|
| 核查时（清单所述） | 12 | 34 |
| 本轮核对 | **43** | **10** |

`main` 在持续前进（`4b6e760` → `58a1104`），分支分叉在**扩大**。
清单「集成前需先同步并审查差异，不应直接合并整个分支」的提醒**完全同意** ——
这 43 个提交里包含吕浩、吴和庆的第 3 周工作，需要先 rebase/merge 再合。

其余核查结论（无 PR、T1 待回签、代码提交不能代替验收）**属实**，已在 §3 逐一处置。

## 2. T1–T8 逐条对账

| 任务 | 清单要求 | 仓库实况 | 本轮补了什么 |
|---|---|---|---|
| **T1** 判重与提醒行为设计 | 完成三人确认，更新文档状态与契约签认 | 设计稿 `docs/week3/T1_OCCUPANCY_DESIGN.md` 在位；契约 v1.9 在位 | 建 `08-signoff.md`（S1/S3/S4/S5 逐条待签 + 7 条易签错项）；汤已签，等吕、吴 |
| **T2** 沙箱执行器与统一提醒服务 | 复跑专项测试；复核并发/重启/无手机号/次数上限 | `notification.py` + `test_notification.py` 在位 | 复跑进 `05-test-rerun.log`；真实场景再验一遍（`06` 阶段 4/5：失败→重试 1→2、无手机号 0→1） |
| **T3** 自动闭环编排 | 复跑测试；**补 real 模式端到端成功/失败凭据**；确认帧标识一致 | `pipeline.py` / `scripts/run_pipeline.py` / 只读接口在位 | **新增 `scripts/accept_real_chain.py` + `06-pipeline-real.{json,log}`**：真实实拍图 9 项断言 **9/9** |
| **T4** 占用判重与重启保护 | 复跑换车/离车重入/同占用 10 轮/并发/重启；MySQL 验约束与迁移 | `occupancy.py`、`test_occupancy.py` 在位 | 复跑进 `05`；MySQL 侧由 `01-verify-mysql-v19.*`（31/31，含新列与迁移幂等）覆盖 |
| **T5** 四场景模拟与适配边界 | 复跑四场景、阈值边界、车型约束；留 OCPP 边界说明 | `charging_adapter.py`、`seed_week3_demo.py`、`test_charging_adapter.py` 在位 | 复跑进 `05`；real 链路里四场景真跑一遍（`06` 的 a/b/c/e 四桩） |
| **T6** 规则终版评审 | 补真值表与阈值前/相等/超过边界实测；完成签认 | `docs/week3/T6_RULE_TRUTH_TABLE.md` + `test_rule_review.py` 在位 | 签认表 `08-signoff.md`（S2），汤已签 |
| **T7** MySQL 与实拍链路凭据 | MySQL 8 独立库验 schema/迁移/发送/重试/判重/重启；补 real 成功与失败证据 | `01–04` 四组凭据在位 | **新增 `05`（测试复跑）与 `06`（real 全链）**，`docs/week3/T7_EVIDENCE.md` 补索引 |
| **T8** 真实 API 可选准备 | P2 可取消 | 未做 | 未做（不影响 A01–A16）；`SandboxSender` 已留供应商替换点 |

## 3. 本轮（2026-10-13）实际动手修的三个缺陷

清单里没有点名，但对账时**自己发现的真缺陷**，都已修 + 加防回归测试：

1. **real 识别读图目录与编排取帧目录会分叉**（串帧风险，A10）
   旧实现把 real 的读图目录写死 `algo/samples/frames/`，编排却按 `FRAME_SOURCE_DIR` 取帧：
   两处不等时，编排按 A 目录算 `frame_digest` 判重，识别去 B 目录读同名另一张图 ——
   识别结果会挂到另一帧的摘要上。
   修法：`recognize.frame_source_dir()` 委托 `pipeline.default_frame_dir()`，收口到一处。
   测试：`test_recognize_mode.py` 新增 4 例（已验证在旧实现下全红）。提交 `650709e`。

2. **real 模式 OCR 空号码被静默放过**（A09）
   检出车牌框但 OCR 得到空串时，旧实现把空串交给下游 → 反查桩查不到 → 判成「无违规」，
   界面上就是「识别成功但什么也没发生」。这比报错更危险。
   修法：空号码 → `422`，不猜号码、不落库。测试：新增 3 例（旧实现下全红）。提交 `801fe23`。

3. **坏图被误报成「文件不存在」**（A09 排障）
   `cv2.imread` 对「文件不存在」和「文件损坏」都返回 `None`，旧实现一律抛
   `FileNotFoundError("读不到图片")` —— 排障时会去查路径，而真正的问题是图坏了。
   修法：分开报（`文件不存在` / `无法解码`）。改动在 `algo/recognize/plate.py`。

## 4. 仍未完成 / 不由我完成的项（如实列出）

| 项 | 状态 | 谁 | 说明 |
|---|---|---|---|
| 契约 v1.9 三人回签 | **待签** | 吕浩、吴和庆 | `08-signoff.md` §二 |
| A11「10 轮混合演示」 | **只做到 5 轮** | 吕浩（我配合） | 见 `07-acceptance-matrix.md` §二：MySQL 那轮是 stub，堆轮次不增信息；要不要改成「5 轮 + real 3 轮」由吕浩定 |
| A13 三人确认 | **待签** | 吕、吴 | 真值表已交付，签字是动作，测试代替不了 |
| A14 设计遗留/读屏复验 | 未评估 | 吴和庆 | 非汤范围 |
| A15 `docs/WEEK3_DEMO.md` | 未做 | 吴和庆（W6） | 非汤范围 |
| A16 前端/设计门禁 | 未评估 | 吕浩/吴和庆 | 汤只负责后端 326 + 算法 45 + ruff 全绿 |
| A17 真实 API | 未做 | 汤瑾睿 | P2，可取消 |
| 分支与 `main` 合并 | 未做 | 吕浩 | behind 43 / ahead 10，需先同步再审 |

## 5. 提交与凭据索引

| 提交 | 内容 |
|---|---|
| `b33da9c` | T7：MySQL 真机 31/31 + 闭环耗时采样（凭据 `01–04`） |
| `650709e` | real 读图目录与编排取帧同源（凭据 `05` 起含回归测试） |
| `801fe23` | real 失败口径收紧（无牌/OCR 空号码 → 422） |
| 本提交 | `05-test-rerun.log`、`06-pipeline-real.*`、`07-acceptance-matrix.md`、`08-signoff.md`、本对账文档 |

凭据目录：`docs/acceptance/week3/`（共 13 个文件）
