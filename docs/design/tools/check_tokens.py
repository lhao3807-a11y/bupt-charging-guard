#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设计令牌校验（docs/design/tokens.css + 线框）

按 AGENTS.md「每次改动必须编写/更新测试，交付前全部通过」的要求，
给设计资产提供可自动跑的验证入口。纯标准库，无第三方依赖。

    python docs/design/tools/check_tokens.py

校验项：
  1. tokens.css 可解析、无重复令牌名
  2. 必需令牌齐全（前端契约：这些名字吕浩会直接引用，不能少）
  3. 颜色令牌取值合法（#hex 或已定义的 var() 引用）
  4. 对比度：白底文字/图形 ≥ 4.5:1、浅底标签文字 ≥ 4.5:1、
     实心填充上的文字 ≥ 4.5:1（WCAG 2.1 AA）
  5. 线框 HTML 不出现裸色值，且引用的每个 var(--x) 都已定义
  6. assets/ 下素材文件名符合 kebab-case 命名规范

退出码 0 = 全部通过；1 = 存在失败项。
"""

import os
import re
import sys
import unicodedata

# ---------------------------------------------------------------- 路径
SCRIPT = os.path.abspath(__file__)
DESIGN_DIR = os.path.dirname(os.path.dirname(SCRIPT))      # docs/design
REPO_ROOT = os.path.dirname(os.path.dirname(DESIGN_DIR))   # 仓库根
TOKENS_CSS = os.path.join(DESIGN_DIR, "tokens.css")
WIREFRAME_DIR = os.path.join(DESIGN_DIR, "wireframes")
ASSETS_DIR = os.path.join(DESIGN_DIR, "assets")

# ---------------------------------------------------------------- WCAG 工具


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError("不是合法的 6 位十六进制色值: #%s" % h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(h):
    r, g, b = hex_to_rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- 解析 tokens.css

TOKEN_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
# 线框内联的 tokens 快照块（见 wireframes/*.html 顶部注释）
SNAPSHOT_RE = re.compile(r'<style[^>]*id="tokens-snapshot"[^>]*>(.*?)</style>', re.S)


def normalize(value):
    """折叠空白并统一小写，便于跨文件比较令牌取值。"""
    return re.sub(r"\s+", " ", value or "").strip().lower()


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_tokens(path):
    css = strip_comments(open(path, encoding="utf-8").read())
    tokens, duplicates = {}, []
    for name, raw in TOKEN_RE.findall(css):
        if name in tokens:
            duplicates.append(name)
        tokens[name] = raw.strip()
    return tokens, duplicates


def resolve(tokens, name, depth=0):
    """把 var(--x) 链解析成最终字面值；解析不出返回 None。"""
    if depth > 8 or name not in tokens:
        return None
    val = tokens[name]
    m = re.fullmatch(r"var\(\s*(--[a-zA-Z0-9-]+)\s*\)", val)
    if m:
        return resolve(tokens, m.group(1), depth + 1)
    return val


def as_hex(tokens, name):
    v = resolve(tokens, name)
    if v and HEX_RE.match(v):
        return v
    return None


# ---------------------------------------------------------------- 预期契约

# 前端会直接引用的令牌名，少一个都算缺
REQUIRED = [
    "--brand-primary", "--brand-primary-hover", "--brand-primary-active",
    "--brand-primary-bg", "--brand-primary-border",
    "--brand-primary-light-3", "--brand-primary-light-5",
    "--brand-primary-light-7", "--brand-primary-light-8",
    "--brand-primary-light-9",
    "--state-danger-solid", "--state-danger-text", "--state-danger-bg", "--state-danger-border",
    "--state-caution-solid", "--state-caution-text", "--state-caution-bg", "--state-caution-border",
    "--state-warning-solid", "--state-warning-text", "--state-warning-bg", "--state-warning-border",
    "--state-success-solid", "--state-success-text", "--state-success-bg", "--state-success-border",
    "--state-info-solid", "--state-info-text", "--state-info-bg", "--state-info-border",
    "--plate-new-energy-text", "--plate-new-energy-bg", "--plate-new-energy-border",
    "--plate-fuel-text", "--plate-fuel-bg", "--plate-fuel-border",
    "--text-primary", "--text-secondary", "--text-tertiary", "--text-disabled",
    "--text-inverse", "--border-base", "--border-strong", "--border-light",
    "--fill-light", "--bg-page", "--bg-container",
    "--font-family-base", "--font-family-mono",
    "--font-size-xs", "--font-size-sm", "--font-size-base", "--font-size-md",
    "--font-size-lg", "--font-size-xl", "--font-size-2xl",
    "--radius-xs", "--radius-sm", "--radius-md", "--radius-lg", "--radius-xl",
    "--radius-pill",
    "--space-1", "--space-2", "--space-3", "--space-4", "--space-5",
    "--space-6", "--space-8", "--space-10", "--space-12",
    "--shadow-sm", "--shadow-md", "--shadow-lg",
    "--layout-sidebar-width", "--layout-sidebar-collapsed-width",
    "--layout-header-height", "--layout-gutter",
    "--el-color-primary", "--el-color-primary-light-9", "--el-color-primary-dark-2",
    "--el-color-success", "--el-color-warning", "--el-color-danger", "--el-color-info",
    "--el-text-color-primary", "--el-text-color-regular",
    "--el-border-color", "--el-bg-color-page",
    "--el-font-size-base", "--el-border-radius-base",
]

# 状态色四档：text 档在白底、自身浅底上都要 ≥ 4.5
STATES = ["danger", "caution", "warning", "success", "info"]

# 纯色块上的文字对照：(前景, 背景, 说明, 是否要求 4.5)
PAIR_CHECKS = [
    ("--text-inverse", "--brand-primary", "主按钮（白字/主色底）", 4.5),
    ("--brand-primary", "--bg-container", "主色文字/链接（白底）", 4.5),
    ("--brand-primary", "--brand-primary-bg", "主色标签（浅底）", 4.5),
    ("--text-primary", "--bg-container", "正文（白底）", 4.5),
    ("--text-primary", "--bg-page", "正文（页面底）", 4.5),
    ("--text-secondary", "--bg-container", "次要正文（白底）", 4.5),
    ("--text-secondary", "--fill-light", "次要正文（浅底/表头）", 4.5),
    ("--text-tertiary", "--bg-container", "说明文字（白底）", 4.5),
    ("--text-tertiary", "--bg-page", "说明文字（页面底）", 4.5),
    ("--text-tertiary", "--fill-light", "说明文字（浅底/表头）", 4.5),
    ("--plate-new-energy-text", "--plate-new-energy-bg", "新能源标签（绿牌绿）", 4.5),
    ("--plate-fuel-text", "--plate-fuel-bg", "燃油标签（蓝牌蓝）", 4.5),
]

# WCAG 1.4.3 豁免项：失效/禁用状态的界面组件不设对比度要求。
# 这里只做提示、不阻断，避免为了通过数字牺牲「禁用态应当弱化」的语义。
EXEMPT_CHECKS = [
    ("--text-disabled", "--bg-container", "禁用文字（白底）"),
]

FAILURES = []
WARNINGS = []


def fail(msg):
    FAILURES.append(msg)


def warn(msg):
    WARNINGS.append(msg)


# ---------------------------------------------------------------- 1~3 解析与完整性


def check_parse_and_completeness(tokens, duplicates):
    print("=" * 78)
    print("[1] 解析与完整性  %s" % os.path.relpath(TOKENS_CSS, REPO_ROOT))
    print("=" * 78)

    for name in duplicates:
        fail("重复定义：%s" % name)
    print("  令牌总数：%d，重复定义：%d" % (len(tokens), len(duplicates)))

    missing = [r for r in REQUIRED if r not in tokens]
    for m in missing:
        fail("缺少必需令牌：%s" % m)
    print("  必需令牌：%d/%d 齐全" % (len(REQUIRED) - len(missing), len(REQUIRED)))

    # 颜色类令牌取值合法性
    bad_value = []
    for name, val in tokens.items():
        if not name.startswith("--"):
            continue
        is_colorish = ("color" in name or "brand" in name or "state" in name
                       or name.startswith("--bg") or name.startswith("--border")
                       or name.startswith("--fill") or name.startswith("--plate")
                       or name.startswith("--text-"))
        if not is_colorish:
            continue
        if HEX_RE.match(val) or val.startswith("var(") or val.startswith("color-mix(") \
                or val.startswith("rgba(") or val.startswith("rgb("):
            continue
        bad_value.append("%s: %s" % (name, val))
    for b in bad_value:
        fail("颜色令牌取值非法（应为 #hex / var() / color-mix() / rgb(a)）：%s" % b)
    print("  取值非法：%d" % len(bad_value))
    print()


# ---------------------------------------------------------------- 4 对比度


def check_contrast(tokens):
    print("=" * 78)
    print("[2] WCAG 2.1 AA 对比度（阈值 4.5:1 正文 / 3:1 大字与图形）")
    print("=" * 78)

    print("  -- 状态色四档 --")
    print("  %-10s %-22s %-22s %-12s" % ("状态", "text 档 / 白底", "text 档 / 自身浅底", "solid 档 / 白底"))
    for s in STATES:
        t = as_hex(tokens, "--state-%s-text" % s)
        bg = as_hex(tokens, "--state-%s-bg" % s)
        solid = as_hex(tokens, "--state-%s-solid" % s)
        if not (t and bg and solid):
            fail("状态 %s 的三档色值无法解析为十六进制" % s)
            continue
        c_white = contrast(t, "#FFFFFF")
        c_tint = contrast(t, bg)
        c_solid = contrast(solid, "#FFFFFF")
        flag_w = "OK" if c_white >= 4.5 else "FAIL"
        flag_t = "OK" if c_tint >= 4.5 else "FAIL"
        # solid 是实心填充档，白底上不要求 4.5，低于 4.5 时给出图形阈值提示
        flag_s = "OK" if c_solid >= 3.0 else "低（仅可作填充）"
        print("  %-10s %-22s %-22s %-12s"
              % (s, "%.2f %s" % (c_white, flag_w), "%.2f %s" % (c_tint, flag_t),
                 "%.2f %s" % (c_solid, flag_s)))
        if c_white < 4.5:
            fail("--state-%s-text 在白底仅 %.2f，低于 4.5（该档用于白底文字/图形）" % (s, c_white))
        if c_tint < 4.5:
            fail("--state-%s-text 在自身浅底仅 %.2f，低于 4.5（标签文字不可读）" % (s, c_tint))
        if c_solid < 3.0:
            warn("--state-%s-solid 在白底 %.2f，<3.0，只能当有色块填充，不可作白底图形" % (s, c_solid))
    print()

    print("  -- 文字与标签配对 --")
    for fg_name, bg_name, desc, need in PAIR_CHECKS:
        fg, bg = as_hex(tokens, fg_name), as_hex(tokens, bg_name)
        if not (fg and bg):
            fail("%s：配色无法解析（%s / %s）" % (desc, fg_name, bg_name))
            continue
        c = contrast(fg, bg)
        ok = c >= need
        print("  %-28s %-24s %.2f  %s" % (desc, "%s on %s" % (fg, bg), c, "OK" if ok else "FAIL"))
        if not ok:
            fail("%s 对比度 %.2f < %.1f（%s 在 %s 上）" % (desc, c, need, fg, bg))
    print()

    print("  -- WCAG 1.4.3 豁免项（仅提示，不阻断） --")
    for fg_name, bg_name, desc in EXEMPT_CHECKS:
        fg, bg = as_hex(tokens, fg_name), as_hex(tokens, bg_name)
        if not (fg and bg):
            fail("%s：配色无法解析（%s / %s）" % (desc, fg_name, bg_name))
            continue
        c = contrast(fg, bg)
        print("  %-28s %-24s %.2f  %s" % (desc, "%s on %s" % (fg, bg), c, "豁免"))
        warn("%s 对比度 %.2f，低于 4.5；依 WCAG 1.4.3 禁用态豁免，但不得承载有效信息"
             % (desc, c))
    print()

    # 实心填充上的文字（白字 or 深字），取两者较优
    print("  -- 实心填充块上的文字（白字或深字取优） --")
    for s in STATES:
        solid = as_hex(tokens, "--state-%s-solid" % s)
        if not solid:
            continue
        best = max(contrast("#FFFFFF", solid), contrast("#1F2329", solid))
        tone = "白字" if contrast("#FFFFFF", solid) >= contrast("#1F2329", solid) else "深字 #1F2329"
        ok = best >= 4.5
        print("  %-10s %s  最优 %.2f（%s）  %s" % (s, solid, best, tone, "OK" if ok else "FAIL"))
        if not ok:
            fail("--state-%s-solid 上无论白字还是深字都不足 4.5（最优 %.2f）" % (s, best))
    print()


# ---------------------------------------------------------------- 5 线框


def check_wireframes(tokens):
    print("=" * 78)
    print("[3] 线框：令牌快照一致性 + 不出现裸色值")
    print("=" * 78)

    if not os.path.isdir(WIREFRAME_DIR):
        warn("线框目录不存在：%s" % WIREFRAME_DIR)
        print("  跳过")
        print()
        return

    files = [f for f in sorted(os.listdir(WIREFRAME_DIR)) if f.lower().endswith((".html", ".htm"))]
    if not files:
        warn("线框目录下没有 HTML 文件")
    for f in files:
        path = os.path.join(WIREFRAME_DIR, f)
        text = open(path, encoding="utf-8").read()
        body = strip_comments(text)

        # --- 3.1 内联令牌快照必须与 tokens.css 一致（防漂移） ---
        snap_m = SNAPSHOT_RE.search(body)
        snap_count, drift = 0, []
        if snap_m:
            snap_tokens = dict(TOKEN_RE.findall(snap_m.group(1)))
            snap_count = len(snap_tokens)
            for name, raw in snap_tokens.items():
                if name not in tokens:
                    drift.append("%s（tokens.css 中不存在）" % name)
                    continue
                a = normalize(resolve(tokens, name))
                b = normalize(resolve(snap_tokens, name))
                if a != b:
                    drift.append("%s：快照 %s ≠ tokens.css %s" % (name, b, a))
            body = body[:snap_m.start()] + body[snap_m.end():]
        else:
            warn("%s 没有内联 tokens 快照；单独打开时可能无样式" % f)

        # --- 3.2 除快照外不得出现裸色值 ---
        bare = []
        for i, line in enumerate(body.splitlines(), 1):
            if "token-exempt" in line:
                continue
            for m in re.finditer(r"#[0-9A-Fa-f]{3,8}\b", line):
                bare.append("L%d: %s" % (i, m.group(0)))

        # --- 3.3 引用的令牌必须已定义 ---
        used = set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", body))
        snap_names = set(dict(TOKEN_RE.findall(snap_m.group(1)))) if snap_m else set()
        undefined = sorted(u for u in used
                           if u not in tokens and u not in snap_names)

        print("  %s" % f)
        print("    内联快照 %3d 项，与 tokens.css 漂移 %d 项" % (snap_count, len(drift)))
        print("    引用令牌 %3d 个，未定义 %d 个，裸色值 %d 处"
              % (len(used), len(undefined), len(bare)))
        for d in drift:
            fail("%s 令牌快照与 tokens.css 不一致 → %s（请重新生成快照）" % (f, d))
        for u in undefined:
            fail("%s 引用了未定义令牌 %s" % (f, u))
        for b in bare:
            fail("%s 出现裸色值 %s（请改用 var(--token)）" % (f, b))
    print()


# ---------------------------------------------------------------- 6 素材命名


def kebab_ok(name):
    stem = os.path.splitext(name)[0]
    if not stem:
        return True
    if unicodedata.category(stem[0]).startswith("L") or stem[0].isdigit():
        pass
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", stem))


def check_assets():
    print("=" * 78)
    print("[4] 素材命名规范（kebab-case）")
    print("=" * 78)

    if not os.path.isdir(ASSETS_DIR):
        warn("素材目录不存在：%s" % ASSETS_DIR)
        print("  跳过")
        print()
        return

    bad, checked = [], 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for name in files:
            if name == ".gitkeep":
                continue
            checked += 1
            if not kebab_ok(name):
                bad.append(os.path.relpath(os.path.join(root, name), REPO_ROOT))
    for b in bad:
        fail("素材文件名不符合 kebab-case：%s" % b)
    print("  检查 %d 个文件，不合规 %d 个" % (checked, len(bad)))
    print()


# ---------------------------------------------------------------- main


def main():
    if not os.path.isfile(TOKENS_CSS):
        print("找不到 tokens.css：%s" % TOKENS_CSS)
        return 1

    tokens, duplicates = parse_tokens(TOKENS_CSS)

    check_parse_and_completeness(tokens, duplicates)
    check_contrast(tokens)
    check_wireframes(tokens)
    check_assets()

    print("=" * 78)
    if WARNINGS:
        print("[警告] %d 项（不阻断）" % len(WARNINGS))
        for w in WARNINGS:
            print("  - %s" % w)
    if FAILURES:
        print("[失败] %d 项" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        print("=" * 78)
        print("结果：未通过")
        return 1
    print("[通过] 设计令牌全部校验通过")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
