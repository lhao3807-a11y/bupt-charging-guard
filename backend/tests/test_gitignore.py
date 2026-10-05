""".gitignore 重型目录守卫测试。

**为什么要有这条测试**：第 2 周真踩过 —— `.gitignore` 里写成

    algo/dataset_raw/   # 公开数据集原始压缩包

而 `.gitignore` **不支持行尾注释**，整行被当成模式，`algo/dataset_raw/` 因此
**根本没被忽略**，865 MB 的 CCPD 压缩包一直挂在 `git status` 的 `??` 里，
差点被 `git add .` 一起提交上去（1.5 GB + 865 MB，推上去基本救不回来）。

这条测试用 `git check-ignore` 直接问 Git，比手写正则可靠 —— 规则解释权交给 Git 自己。

运行方式::

    .venv\\Scripts\\python.exe -m pytest backend/tests -q
"""

from __future__ import annotations

import os
import subprocess

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

#: 这些目录体积大、可本地重新生成，**绝不能**入库
HEAVY_DIRS = (
    "algo/dataset",
    "algo/dataset_raw",
    "algo/dataset_real",
    "algo/weights",
    "algo/runs",
)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=False
    )


def test_heavy_dirs_are_ignored():
    for rel in HEAVY_DIRS:
        path = os.path.join(REPO, rel)
        if not os.path.isdir(path):
            continue  # 本地没生成就跳过，规则本身仍被下一条测试覆盖
        r = _git("check-ignore", "-q", rel)
        assert r.returncode == 0, f"{rel} 居然没被 .gitignore 忽略（会把几百 MB 提交上去）"


def test_gitignore_has_no_inline_comments():
    """行尾注释会让整行变成模式，是本次事故的直接原因 —— 禁止再出现。"""
    with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            assert "#" not in line, (
                f".gitignore 第 {lineno} 行含行尾注释：{line!r}\n"
                "git 不支持行尾注释，整行会被当成匹配模式而失效，请把注释单独写一行。"
            )
