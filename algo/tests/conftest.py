"""algo/tests 共享 fixture：把仓库根目录加入 sys.path，保证 ``import algo.*`` 可用。

**CV 环境守卫（第 2 周任务 5.2）**
算法依赖（``numpy`` / ``cv2`` / ``ultralytics``）只在**算法环境**里装
（见 ``algo/requirements-algo.txt``），后端开发机与 CI 上通常没有。
此前模块级 ``import numpy`` 会让 pytest 在**收集阶段**就 ``ImportError``，
退出码 **2**，看起来像「测试挂了」，实际只是环境没装 —— 真出问题时反而被噪音淹没。

守卫做法：每个测试模块在导入期先 ``pytest.importorskip(...)``，缺依赖 →
该模块**跳过（skipped）**，退出码 0；装上依赖后行为完全不变。

> ⚠️ **不要在 conftest 顶层调 `pytest.skip`**：conftest 是在 pytest 启动阶段加载的，
> 此时抛 `Skipped` 不会被当成用例跳过，而是直接把整个 pytest 进程打崩（exit 1）。
> 守卫必须写在**测试模块**里。
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

#: 算法环境的最小哨兵依赖（各测试模块据此 importorskip）
CV_REQUIREMENTS = ("numpy", "cv2")
