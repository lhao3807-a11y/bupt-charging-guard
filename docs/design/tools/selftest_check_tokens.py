#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_tokens.py 的反例自测：确认每条断言真的会拦下违规，而不是空跑。

做法：逐个用例把设计资产「改坏」→ 跑 check_tokens.py → 期望 exit 1 且出现对应失败信息
→ 无论成败都还原原文件。全部用例通过后复跑一次，确认基线仍是绿的。

    python docs/design/tools/selftest_check_tokens.py

为什么需要它：`check_tokens.py` 报「全部通过」有两种可能 —— 资产确实合规，
或者断言写错了根本没查到。这个脚本能区分这两种情况。
结论记录见 `docs/design/walkthrough.md` §3。

纯标准库，无第三方依赖。
"""

import os
import shutil
import subprocess
import sys

SCRIPT = os.path.abspath(__file__)
TOOLS_DIR = os.path.dirname(SCRIPT)                       # docs/design/tools
DESIGN_DIR = os.path.dirname(TOOLS_DIR)                   # docs/design
REPO_ROOT = os.path.dirname(os.path.dirname(DESIGN_DIR))  # 仓库根

CHECKER = os.path.join(TOOLS_DIR, "check_tokens.py")
REC = os.path.join(DESIGN_DIR, "wireframes", "records.html")
STAT = os.path.join(DESIGN_DIR, "wireframes", "statistics.html")
ICON = os.path.join(DESIGN_DIR, "assets", "icons", "icon-search.svg")

# (用例名, 目标文件, 原串, 替换串, 期望出现的失败信息, 是否替换全部)
CASES = [
    ("自造字段列", REC,
     '<th style="width: 120px;">操作</th>',
     '<th style="width: 120px;">自造字段</th>',
     "表格列名超出契约字段白名单", False),
    ("导航文案与契约不符", REC,
     '<span class="nav-idx">1</span>车辆信息管理',
     '<span class="nav-idx">1</span>车辆管理',
     "导航 6 项与契约", False),
    ("当前页高亮丢失", REC,
     '<a class="nav-item is-active"><span class="nav-idx">2</span>违规记录查询</a>',
     '<a class="nav-item"><span class="nav-idx">2</span>违规记录查询</a>',
     "当前页高亮", False),
    ("缺少空态区块", REC,
     '<div class="empty">',
     '<div class="emptybox">',
     "缺少空态区块", True),
    ("间距脱离 4px 栅格", REC,
     "padding: var(--space-5) var(--layout-gutter) var(--space-10);",
     "padding: 20px 24px 40px;",
     "间距出现裸 px 值", False),
    ("裸色值", REC,
     '<td class="mono num">1</td>',
     '<td class="mono num" style="color: #A8071A;">1</td>',
     "出现裸色值", False),
    ("tokens 快照漂移", REC,
     "  --brand-primary: #1668E3;",
     "  --brand-primary: #1668E4;",
     "令牌快照与 tokens.css 不一致", False),
    ("图标写死色值", ICON,
     'stroke="currentColor"',
     'stroke="#A8071A"',
     "不得写死色值", False),
    # 2026-09-19 终检补入：第 4 页下钻表与第 2 页读同一张 occupation_record，
    # 若把「车牌」写成「车牌号」，白名单和同表跨页比对应同时拦下。
    ("同表跨页列名分叉", STAT,
     '<th style="width: 150px;">车牌</th>',
     '<th style="width: 150px;">车牌号</th>',
     "列名分叉", False),
]


def run_checker():
    r = subprocess.run([sys.executable, CHECKER], cwd=REPO_ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def main():
    if not os.path.isfile(CHECKER):
        print("找不到 check_tokens.py：%s" % CHECKER)
        return 1

    code, out = run_checker()
    if code != 0:
        print("基线不是绿的，先修好资产再来测断言：")
        print(out[-2000:])
        return 1
    print("基线 exit=0 ✓")
    print()

    failed = []
    for name, path, old, new, expect, replace_all in CASES:
        bak = path + ".selftest.bak"
        shutil.copy2(path, bak)
        try:
            text = open(bak, encoding="utf-8").read()
            if old not in text:
                print("  %-16s 锚点不存在，用例需更新" % name)
                failed.append(name + "(锚点缺失)")
                continue
            open(path, "w", encoding="utf-8", newline="").write(
                text.replace(old, new) if replace_all else text.replace(old, new, 1))
            code, out = run_checker()
            hit = expect in out
            ok = (code == 1 and hit)
            print("  %-16s exit=%d  失败信息命中=%s  %s"
                  % (name, code, "是" if hit else "否", "✓" if ok else "✗ 未拦下"))
            if not ok:
                failed.append(name)
        finally:
            shutil.copy2(bak, path)
            os.remove(bak)

    code, out = run_checker()
    print()
    print("还原后复跑 exit=%d（应为 0）%s" % (code, "✓" if code == 0 else "✗"))
    if failed:
        print("未通过的用例：%s" % " / ".join(failed))
        return 1
    print("全部 %d 个用例：改坏即被拦下 ✓" % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
