#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_tokens.py 的反例自测：确认每条断言真的会拦下违规，而不是空跑。

做法：逐个用例把设计资产「改坏」→ 跑 check_tokens.py → 期望 exit 1 且出现对应失败信息
→ 无论成败都还原原文件。全部用例通过后复跑一次，确认基线仍是绿的。

    python docs/design/tools/selftest_check_tokens.py

为什么需要它：`check_tokens.py` 报「全部通过」有两种可能 —— 资产确实合规，
或者断言写错了根本没查到。这个脚本能区分这两种情况。
结论记录见 `docs/design/walkthrough.md` §3。

三类用例：
  * CASES        —— 文本替换（改坏某个文件里的一段内容）
  * MISSING_CASES —— 文件级整体缺失（把文件临时移走，模拟「交付物没交」）
  * BINARY_CASES —— 二进制文件替换（PNG 不能用文本替换改坏，只能整块换掉）

纯标准库，无第三方依赖。
"""

import os
import shutil
import struct
import subprocess
import sys
import zlib

SCRIPT = os.path.abspath(__file__)
TOOLS_DIR = os.path.dirname(SCRIPT)                       # docs/design/tools
DESIGN_DIR = os.path.dirname(TOOLS_DIR)                   # docs/design
REPO_ROOT = os.path.dirname(os.path.dirname(DESIGN_DIR))  # 仓库根

CHECKER = os.path.join(TOOLS_DIR, "check_tokens.py")
REC = os.path.join(DESIGN_DIR, "wireframes", "records.html")
STAT = os.path.join(DESIGN_DIR, "wireframes", "statistics.html")
PREVIEW = os.path.join(DESIGN_DIR, "wireframes", "preview.html")
ICON = os.path.join(DESIGN_DIR, "assets", "icons", "icon-search.svg")
CONTRACT = os.path.join(REPO_ROOT, "docs", "CONTRACT.md")
INV = os.path.join(DESIGN_DIR, "component-inventory.md")
RAW_SHOT = os.path.join(DESIGN_DIR, "demo", "screenshots", "raw", "login.png")

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
    # --- 2026-09-19 补入：列名白名单已改为从 CONTRACT.md §3.5 派生，
    #     下面 4 条验证「改契约就能拦下」这件事真的成立（而非断言空跑）。
    ("§3.5 同表跨页列名分叉", CONTRACT,
     "| plate | 车牌 | P2 |",
     "| plate | 车牌号 | P2 |",
     "同表同字段", False),
    ("§3.5 改列名致线框越界", CONTRACT,
     "| phone | 手机号 | P1 |",
     "| phone | 手机 | P1 |",
     "超出契约字段白名单", False),
    ("§3.1 说明档与 §3.5 漂移", CONTRACT,
     "| plate | VARCHAR(15) PK | 车牌号 |",
     "| plate | VARCHAR(15) PK | 车牌 |",
     "说明档", False),
    ("§3.5 整节缺失", CONTRACT,
     "### 3.5 显示列名映射表",
     "### 3.5X 已移除",
     "无法从 CONTRACT.md §3.5 解析", False),
    # --- 2026-09-26 第 2 周补入：覆盖本轮新增/反转的断言 ---
    # 导航解禁断言从「恰有 1 个 is-reserved」反转为「不得有」，
    # 必须证明**反转后的断言**也在工作（只反转不验证 = 新的空跑风险）。
    ("第 6 页被重新置灰", PREVIEW,
     '<a class="nav-item is-active"><span class="nav-idx">6</span>实时识别预览</a>',
     '<a class="nav-item is-active is-reserved"><span class="nav-idx">6</span>实时识别预览</a>',
     "不应再有 is-reserved", False),
    # 加载态规格（任务 6.2）：章节没了必须拦下
    ("§2.1 加载态规格缺失", INV,
     "### 2.1 加载态规格",
     "### 2.1X 已移除",
     "缺 §2.1 加载态规格", False),
    # 骨架屏样张（任务 6.2/6.12）：把所有独立 skeleton 类名改掉
    ("骨架屏样张缺失", PREVIEW,
     'class="skeleton',
     'class="skel',
     "缺骨架屏样张", True),
    # 线框登记（任务 6.12）：把 §3.5 里**全部** P6 行挪到不存在的 P7，
    # 第 6 页会从派生结果里整个消失 → 该页的导航/空态/列名/间距校验全被跳过。
    # 必须失败而非静默。注意要整页搬走：只挪一行的话该页仍算「已登记」，
    # 只会报「缺少契约字段列」，构造不出「未登记」这个条件（首版用例就是这么写错的）。
    ("线框未登记 §3.5", CONTRACT,
     "| P6 |",
     "| P7 |",
     "未在 CONTRACT.md §3.5 登记", True),
]

# 文件级用例：(用例名, 目标文件, 期望出现的失败信息)
MISSING_CASES = [
    ("第 6 页线框缺失",
     os.path.join(DESIGN_DIR, "wireframes", "preview.html"),
     "第 6 页线框缺失"),
    ("空结果插画缺失",
     os.path.join(DESIGN_DIR, "assets", "illustrations", "empty-state-search-empty.svg"),
     "空态插画缺失"),
    # --- 2026-09-29 第 2 周复验补入：6.10 新增的「美化版必须能追溯到原始实拍图」断言。
    # 这条断言的唯一职责就是拦住「拿线框或旧图冒充实拍」。把 raw/ 里的原件移走，
    # 若还报通过，就说明这道防线是空的（那 6.10 的「不许冒充」等于没守）。
    ("答辩截图缺原始图",
     RAW_SHOT,
     "答辩截图缺原始图"),
]

# 二进制替换用例：(用例名, 目标文件, 写进去的字节, 期望出现的失败信息)
# PNG 没法用文本替换改坏，只能整块换掉。这里换一张尺寸不同的合法 PNG，
# 用来验证「同一批原始图必须同一视口」这条断言真的在比尺寸（而不是只看文件在不在）。
BINARY_CASES = [
    ("答辩截图原图尺寸不一", RAW_SHOT, None, "原始图尺寸不统一"),
]


def make_png(width, height):
    """生成一张 width×height 的合法纯白 PNG（纯标准库，用于打靶）。"""
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


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

    # 文件级：把交付物临时移走，确认「缺失」会被拦下（而不是静默少检一项）
    for name, path, expect in MISSING_CASES:
        if not os.path.isfile(path):
            print("  %-16s 目标文件不存在，用例需更新" % name)
            failed.append(name + "(文件缺失)")
            continue
        hidden = path + ".selftest.hidden"
        try:
            os.rename(path, hidden)
            code, out = run_checker()
            hit = expect in out
            ok = (code == 1 and hit)
            print("  %-16s exit=%d  失败信息命中=%s  %s"
                  % (name, code, "是" if hit else "否", "✓" if ok else "✗ 未拦下"))
            if not ok:
                failed.append(name)
        finally:
            os.rename(hidden, path)

    # 二进制：整块换掉一个 PNG，确认尺寸类断言真的在比对（而不是只查文件是否存在）
    for name, path, data, expect in BINARY_CASES:
        if not os.path.isfile(path):
            print("  %-16s 目标文件不存在，用例需更新" % name)
            failed.append(name + "(文件缺失)")
            continue
        bak = path + ".selftest.bak"
        shutil.copy2(path, bak)
        try:
            with open(path, "wb") as fh:
                fh.write(data if data is not None else make_png(1024, 640))
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
    total = len(CASES) + len(MISSING_CASES) + len(BINARY_CASES)
    if failed:
        print("未通过的用例：%s" % " / ".join(failed))
        return 1
    print("全部 %d 个用例：改坏即被拦下 ✓" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
