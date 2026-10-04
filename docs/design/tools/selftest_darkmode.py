#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_darkmode.py 的反例自测：确认深色方案的每条断言真的会拦下，而不是空跑。

做法：把 `tokens-dark.css` 逐处「改坏」→ 跑 check_darkmode.py → 期望 exit 1 且出现对应
失败信息 → 无论成败都还原原文件。全部用例通过后复跑一次，确认基线仍是绿的。

    python docs/design/tools/selftest_darkmode.py

为什么需要它：`check_darkmode.py` 只对**方案稿**做数值验算，很容易写成「无论怎么改都过」。
本脚本用同一套口径验证它确实在算（第 2 周纪律：每条新断言必须配反例打靶，
见 TASK_WU_WEEK2 任务 6.12）。

结论记录见 `docs/design/walkthrough.md` §9。
"""

import os
import shutil
import subprocess
import sys

SCRIPT = os.path.abspath(__file__)
TOOLS_DIR = os.path.dirname(SCRIPT)                       # docs/design/tools
DESIGN_DIR = os.path.dirname(TOOLS_DIR)                   # docs/design
REPO_ROOT = os.path.dirname(os.path.dirname(DESIGN_DIR))  # 仓库根

CHECKER = os.path.join(TOOLS_DIR, "check_darkmode.py")
DARK = os.path.join(DESIGN_DIR, "tokens-dark.css")

# (用例名, 原串, 替换串, 期望出现的失败信息, 是否替换全部)
CASES = [
    # 深色块必须与浅色令牌集同构：多一个令牌 = 悄悄开了第二套命名
    ("深色引入新令牌",
     "  --bg-mask:                  rgba(0, 0, 0, 0.65);",
     "  --bg-mask:                  rgba(0, 0, 0, 0.65);\n  --dark-only-token:          #123456;",
     "浅色侧不存在的令牌", False),
    # 漏覆盖关键令牌 → 浏览器会回退到浅色值（深底 + 浅字必翻车）
    ("关键令牌漏覆盖",
     "  --border-base:              #33383F;  /* 表格线、输入框描边 */\n",
     "",
     "关键令牌 --border-base 未被深色覆盖", False),
    # 最常见的手滑：复制浅色块没改值
    ("白底残留",
     "  --bg-container:             #1B1F25;",
     "  --bg-container:             #FFFFFF;",
     "仍为浅色值", False),
    # 说明文字是深色模式最容易掉到 4.5 以下的一档
    ("说明文字对比不足",
     "  --text-tertiary:            #8A929C;",
     "  --text-tertiary:            #6A7280;",
     "低于 4.5", False),
    # 三档底的层级方向搞反（page 反而比 container 亮）
    ("底层级颠倒",
     "  --bg-page:                  #0F1115;",
     "  --bg-page:                  #33383F;",
     "层级颠倒", False),
    # 覆盖块选择器写错 → 整块失效（会导致所有「未覆盖」判定连锁失败，须一眼看出）
    ("深色块选择器失配",
     ":root[data-theme='dark'],",
     ":root[data-theme='darkish'],",
     "未找到深色覆盖块", False),
]

# 文件级用例：(用例名, 目标文件, 期望出现的失败信息)
MISSING_CASES = [
    ("方案文件缺失", DARK, "缺少 tokens-dark.css"),
]


def run_checker():
    r = subprocess.run([sys.executable, CHECKER], cwd=REPO_ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def main():
    if not os.path.isfile(CHECKER):
        print("找不到 check_darkmode.py：%s" % CHECKER)
        return 1

    code, out = run_checker()
    if code != 0:
        print("基线不是绿的，先修好方案再来测断言：")
        print(out[-2000:])
        return 1
    print("基线 exit=0 ✓")
    print()

    failed = []
    for name, old, new, expect, replace_all in CASES:
        bak = DARK + ".selftest.bak"
        shutil.copy2(DARK, bak)
        try:
            text = open(bak, encoding="utf-8").read()
            if old not in text:
                print("  %-18s 锚点不存在，用例需更新" % name)
                failed.append(name + "(锚点缺失)")
                continue
            open(DARK, "w", encoding="utf-8", newline="").write(
                text.replace(old, new, -1 if replace_all else 1))
            code, out = run_checker()
            hit = expect in out
            ok = (code == 1 and hit)
            print("  %-18s exit=%d  失败信息命中=%s  %s"
                  % (name, code, "是" if hit else "否", "✓" if ok else "✗ 未拦下"))
            if not ok:
                failed.append(name)
        finally:
            shutil.copy2(bak, DARK)
            os.remove(bak)

    for name, path, expect in MISSING_CASES:
        if not os.path.isfile(path):
            print("  %-18s 目标文件不存在，用例需更新" % name)
            failed.append(name + "(文件缺失)")
            continue
        hidden = path + ".selftest.hidden"
        try:
            os.rename(path, hidden)
            code, out = run_checker()
            hit = expect in out
            ok = (code == 1 and hit)
            print("  %-18s exit=%d  失败信息命中=%s  %s"
                  % (name, code, "是" if hit else "否", "✓" if ok else "✗ 未拦下"))
            if not ok:
                failed.append(name)
        finally:
            os.rename(hidden, path)

    code, out = run_checker()
    print()
    print("还原后复跑 exit=%d（应为 0）%s" % (code, "✓" if code == 0 else "✗"))
    if failed:
        print("未通过的用例：%s" % " / ".join(failed))
        return 1
    print("全部 %d 个用例：改坏即被拦下 ✓" % (len(CASES) + len(MISSING_CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
