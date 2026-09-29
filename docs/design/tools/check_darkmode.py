#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深色模式令牌方案校验（docs/design/tokens-dark.css）

对应第 2 周任务 6.8（深色模式方案）。**本脚本不校验任何页面**，只做两件事：

  1. 深色令牌的**键一致性**：tokens-dark.css 覆盖的令牌必须全部存在于 tokens.css，
     且不得新增浅色侧没有的令牌（防止深色模式悄悄引入第二套命名体系）。
  2. 深色下的**对比度验算**：复用 check_tokens.py 的三档口径（`-text`/白底、
     `-text`/自身浅底、`-solid`/白底），把"白底"换成深色三档底后重新断言。

    python docs/design/tools/check_darkmode.py

退出码 0 = 方案数值全部达标；1 = 存在失败项（改坏即红）。
"""

import os
import re
import sys

SCRIPT = os.path.abspath(__file__)
DESIGN_DIR = os.path.dirname(os.path.dirname(SCRIPT))
TOKENS_CSS = os.path.join(DESIGN_DIR, "tokens.css")
TOKENS_DARK_CSS = os.path.join(DESIGN_DIR, "tokens-dark.css")

# 正文/图形阈值 4.5:1；纯装饰性填充块只要求 3:1
AA_TEXT = 4.5
AA_GRAPHIC = 3.0


# ---------------------------------------------------------------- WCAG 工具


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(h):
    r, g, b = hex_to_rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- 解析

TOKEN_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
# 深色覆盖块：`:root[data-theme='dark'], .theme-dark { ... }`
DARK_BLOCK_RE = re.compile(
    r":root\[data-theme=['\"]dark['\"]\]\s*(?:,\s*\.theme-dark\s*)?\{(.*?)\}", re.S
)

FAILS, WARNS = [], []


def fail(msg):
    FAILS.append(msg)
    print("  ✗ %s" % msg)


def warn(msg):
    WARNS.append(msg)
    print("  ⚠ %s" % msg)


def ok(msg):
    print("  ✓ %s" % msg)


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_tokens(css):
    tokens = {}
    for name, raw in TOKEN_RE.findall(css):
        tokens[name] = raw.strip()
    return tokens


def resolve(tokens, name, depth=0):
    if depth > 8 or name not in tokens:
        return None
    val = tokens[name]
    m = re.fullmatch(r"var\(\s*(--[a-zA-Z0-9-]+)\s*\)", val)
    if m:
        return resolve(tokens, m.group(1), depth + 1)
    return val


def as_hex(tokens, name):
    v = resolve(tokens, name)
    return v if v and HEX_RE.match(v) else None


def check_pair(label, fg, bg, threshold=AA_TEXT, allow_graphic=False):
    """返回 (对比度, 是否达标)；未达标时登记失败或警告。"""
    if not fg or not bg:
        fail("%s —— 取色失败（fg=%s bg=%s，令牌可能未定义）" % (label, fg, bg))
        return None, False
    ratio = contrast(fg, bg)
    passed = ratio >= threshold
    if passed:
        print("  %-34s %s on %s  %5.2f  OK" % (label, fg, bg, ratio))
    elif allow_graphic and ratio >= AA_GRAPHIC:
        print("  %-34s %s on %s  %5.2f  低（仅可作填充）" % (label, fg, bg, ratio))
    else:
        fail("%s —— %s on %s 仅 %.2f，低于 %.1f:1" % (label, fg, bg, ratio, threshold))
    return ratio, passed


def main():
    print("=" * 78)
    print("[深色模式] 令牌方案校验  docs/design/tokens-dark.css")
    print("=" * 78)

    if not os.path.exists(TOKENS_DARK_CSS):
        fail("缺少 tokens-dark.css —— 任务 6.8 交付物未找到")
        return 1

    light = parse_tokens(strip_comments(open(TOKENS_CSS, encoding="utf-8").read()))
    dark_css = strip_comments(open(TOKENS_DARK_CSS, encoding="utf-8").read())
    m = DARK_BLOCK_RE.search(dark_css)
    if not m:
        fail("未找到深色覆盖块 —— 需为 :root[data-theme='dark'] 或 .theme-dark")
        return 1
    dark_overrides = parse_tokens(m.group(1))

    # 深色 = 浅色基座 + 深色覆盖（与浏览器级联一致）
    dark = dict(light)
    dark.update(dark_overrides)

    # ---------------------------------------------------------- 1. 键一致性
    print("\n[1] 键一致性（深色覆盖不得引入浅色侧没有的令牌）")
    unknown = sorted(n for n in dark_overrides if n not in light)
    for n in unknown:
        fail("深色块定义了浅色侧不存在的令牌 %s —— 两套令牌集必须同构" % n)
    if not unknown:
        ok("覆盖 %d 个令牌，全部存在于 tokens.css，无新增命名" % len(dark_overrides))

    # 关键令牌必须被深色覆盖，否则会静默回退到浅色值（最典型：白底残留）
    CRITICAL = [
        "--bg-page", "--bg-container", "--fill-light",
        "--border-base", "--border-light", "--border-strong",
        "--text-primary", "--text-secondary", "--text-tertiary", "--text-inverse",
        "--brand-primary", "--brand-primary-bg",
        "--state-danger-solid", "--state-danger-text", "--state-danger-bg",
        "--state-caution-solid", "--state-caution-text", "--state-caution-bg",
        "--state-warning-solid", "--state-warning-text", "--state-warning-bg",
        "--state-success-solid", "--state-success-text", "--state-success-bg",
        "--state-info-solid", "--state-info-text", "--state-info-bg",
    ]
    missing = [n for n in CRITICAL if n not in dark_overrides]
    if missing:
        for n in missing:
            fail("关键令牌 %s 未被深色覆盖 —— 会回退成浅色值（深底+浅字必翻车）" % n)
    else:
        ok("关键令牌 %d 个全部被覆盖（底/描边/文字/品牌/五档状态色）" % len(CRITICAL))

    # 残留检测：深色块里不该再出现浅色的"白底黑字"取值
    for name, bad in (("--bg-container", "#FFFFFF"), ("--text-primary", "#1F2329")):
        v = as_hex(dark, name)
        if v and v.upper() == bad.upper():
            fail("深色下 %s 仍为浅色值 %s —— 典型的复制漏改" % (name, bad))

    # ---------------------------------------------------------- 2. 底与描边
    print("\n[2] 三档底与描边（层级方向：page 最深 → container → fill-light 更亮）")
    page = as_hex(dark, "--bg-page")
    container = as_hex(dark, "--bg-container")
    fill = as_hex(dark, "--fill-light")
    if page and container and fill:
        if not (relative_luminance(page) < relative_luminance(container) <= relative_luminance(fill)):
            fail("深色三档底层级颠倒：page=%s container=%s fill=%s（应 page 最暗）"
                 % (page, container, fill))
        else:
            ok("层级正确  page %s < container %s < fill %s" % (page, container, fill))
    for a, b, label in ((page, container, "page/container"), (container, fill, "container/fill")):
        if a and b:
            r = contrast(a, b)
            # 深色模式下层差天然比浅色小，层级主要靠描边（--border-base）而不是底差，
            # 因此这里只要求"肉眼可辨"（≥1.10），不套用浅色的口径。
            print("  %-34s %s / %s  %5.2f  %s"
                  % (label, a, b, r, "可辨" if r >= 1.10 else "过近，层级看不清"))
            if r < 1.10:
                fail("深色底 %s 与 %s 对比仅 %.2f —— 层级会糊在一起" % (a, b, r))

    # ---------------------------------------------------------- 3. 文字层级
    print("\n[3] 文字层级 / 深色三档底（阈值 %.1f:1）" % AA_TEXT)
    for name, label in (("--text-primary", "主文字"), ("--text-secondary", "次要文字"),
                        ("--text-tertiary", "说明文字")):
        fg = as_hex(dark, name)
        for bg_name, bg_label in (("--bg-container", "卡片底"), ("--bg-page", "页面底"),
                                  ("--fill-light", "浅底/表头")):
            check_pair("%s（%s）" % (label, bg_label), fg, as_hex(dark, bg_name))
    dis = as_hex(dark, "--text-disabled")
    print("  %-34s %s on %s  %5.2f  豁免（WCAG 1.4.3，不得承载有效信息）"
          % ("禁用文字", dis, container, contrast(dis, container) if dis and container else 0))

    # ---------------------------------------------------------- 4. 状态色三档
    print("\n[4] 状态色四档 × 深色底（`-text`/卡片底、`-text`/自身浅底、`-solid`/卡片底）")
    print("  %-10s %-22s %-22s %s" % ("状态", "text/卡片底", "text/自身浅底", "solid/卡片底"))
    for key in ("danger", "caution", "warning", "success", "info"):
        text = as_hex(dark, "--state-%s-text" % key)
        bg = as_hex(dark, "--state-%s-bg" % key)
        solid = as_hex(dark, "--state-%s-solid" % key)
        check_pair("%s text/卡片底" % key, text, container)
        check_pair("%s text/自身浅底" % key, text, bg)
        check_pair("%s solid/卡片底" % key, solid, container, AA_GRAPHIC, allow_graphic=True)

    # ---------------------------------------------------------- 5. 实心块上的文字
    print("\n[5] 实心填充块上的文字（白字 / 深字取优，阈值 %.1f:1）" % AA_TEXT)
    for key in ("danger", "caution", "warning", "success", "info"):
        solid = as_hex(dark, "--state-%s-solid" % key)
        if not solid:
            fail("--state-%s-solid 取色失败" % key)
            continue
        w, d = contrast("#FFFFFF", solid), contrast(as_hex(dark, "--text-inverse") or "#000000", solid)
        best = max(w, d)
        pick = "白字" if w >= d else "深字 %s" % as_hex(dark, "--text-inverse")
        if best < AA_TEXT:
            fail("%s 实心块 %s 最优仅 %.2f（%s）" % (key, solid, best, pick))
        else:
            print("  %-34s %s  最优 %5.2f（%s）  OK" % (key, solid, best, pick))

    # ---------------------------------------------------------- 6. 主色与标签
    print("\n[6] 品牌主色与业务标签")
    primary = as_hex(dark, "--brand-primary")
    check_pair("主色文字/链接（卡片底）", primary, container)
    check_pair("主色标签（主色浅底）", primary, as_hex(dark, "--brand-primary-bg"))
    if primary:
        inverse = as_hex(dark, "--text-inverse") or "#000000"
        w, d = contrast("#FFFFFF", primary), contrast(inverse, primary)
        best, pick = max((w, "白字"), (d, "深字 %s" % inverse))
        if best < AA_TEXT:
            fail("主按钮（主色底 %s）最优仅 %.2f（%s）" % (primary, best, pick))
        else:
            print("  %-34s %s  最优 %5.2f（%s）  OK" % ("主按钮（主色底）", primary, best, pick))
        # 深色模式的预期是"亮主色底 + 深字"，与浅色模式（主色底 + 白字）正好相反
        if d > w:
            ok("深色下主按钮走深字（--text-inverse=%s）—— 与浅色的白字相反，属预期" % inverse)
        else:
            warn("主按钮在白字下更优 —— 确认主色是否偏暗（深色模式预期以深字为主）")

    print("\n[7] 车牌底色标签（与真实车牌色相呼应，深色版）")
    for key, label in (("new-energy", "新能源（绿牌绿）"), ("fuel", "燃油（蓝牌蓝）")):
        check_pair(label, as_hex(dark, "--plate-%s-text" % key), as_hex(dark, "--plate-%s-bg" % key))

    # ---------------------------------------------------------- 汇总
    print("\n" + "=" * 78)
    if FAILS:
        print("[失败] %d 项" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        print("=" * 78)
        return 1
    print("[通过] 深色方案数值全部达标（本脚本不校验页面；样张见 dark-mode/sample.html）")
    if WARNS:
        print("[警告] %d 项" % len(WARNS))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
