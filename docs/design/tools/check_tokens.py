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
  6. assets/ 下素材文件名符合 kebab-case 命名规范，且取色合规
     （图标只用 currentColor；Logo / 插画只允许 var(--x, #hex) 兜底写法）
  7. 跨页一致性（对应 component-inventory.md §5 的走查清单）：
     导航 6 项顺序、当前页高亮、空态齐备、表头底/行线/悬浮行、
     定长标识用等宽、表格列名 ⊆ 契约字段白名单、间距取 4px 栅格、
     同一张表被多页引用时列名写法一致

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
# 素材里唯一允许出现色值的写法：var(--token, #hex)（以 <img> 引入 CSS 变量不生效，需兜底）
VAR_FALLBACK_RE = re.compile(r"var\(\s*--[a-zA-Z0-9-]+\s*,\s*#[0-9A-Fa-f]{3,8}\s*\)")


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
    print("[4] 素材：命名规范（kebab-case）+ 取色规范")
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
    print("  检查 %d 个文件，命名不合规 %d 个" % (checked, len(bad)))

    # --- 取色规范（README.md §2.2 / §2.4）---
    # 图标：必须 currentColor，不得出现任何色值（写死色值就失去了随主题变色的能力）
    # Logo / 插画：允许 var(--token, #hex) 这种带兜底值的写法（以 <img> 引入时 CSS 变量
    #              不参与级联，兜底值保证独立打开与 img 场景都能显示）
    icons_checked = tint_checked = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for name in sorted(files):
            if not name.lower().endswith(".svg"):
                continue
            rel = os.path.relpath(os.path.join(root, name), REPO_ROOT)
            text = open(os.path.join(root, name), encoding="utf-8").read()
            if os.path.basename(root) == "icons":
                icons_checked += 1
                hexes = re.findall(r"#[0-9A-Fa-f]{3,8}\b", text)
                if hexes:
                    fail("图标不得写死色值（应用 currentColor）：%s → %s"
                         % (rel, ", ".join(sorted(set(hexes)))))
                if "currentColor" not in text:
                    fail("图标未使用 currentColor：%s" % rel)
                if 'viewBox="0 0 24 24"' not in text:
                    fail("图标画布应为 24×24（viewBox 0 0 24 24）：%s" % rel)
                if 'stroke-width="1.5"' not in text:
                    fail("图标描边应为 stroke-width 1.5：%s" % rel)
            else:
                tint_checked += 1
                stripped = VAR_FALLBACK_RE.sub("", text)
                leftovers = re.findall(r"#[0-9A-Fa-f]{3,8}\b", stripped)
                if leftovers:
                    fail("Logo / 插画中的色值只能写成 var(--token, #hex) 兜底形式：%s → %s"
                         % (rel, ", ".join(sorted(set(leftovers)))))
    print("  图标 %d 个（currentColor / 24×24 / 1.5 描边）；Logo+插画 %d 个（兜底形式取色）"
          % (icons_checked, tint_checked))
    print()


# ---------------------------------------------------------------- 7 跨页一致性

# 侧边导航顺序 = CONTRACT.md §1.1 的 6 页顺序
NAV_ORDER = ["车辆信息管理", "违规记录查询", "充电状态展示",
             "报警统计", "系统参数配置", "实时识别预览"]

# 表格列名白名单：列名只允许来自契约定义的表字段（+ 操作列），
# 防止「自造字段」。新增页面/列必须先改 CONTRACT.md 再登记到这里。
COL_操作 = "操作"
CONTRACT_COLUMNS = {
    "vehicle-management.html": {
        "table": "vehicle",
        "allow": {"车牌号", "车型", "车主", "手机号", "录入时间", COL_操作},
        "require": {"车牌号", "车型", "车主", "手机号", "录入时间"},
    },
    "records.html": {
        "table": "occupation_record",
        "allow": {"ID", "车牌", "车型", "桩 ID", "命中规则", "命中时间",
                  "提醒状态", "提醒时间", COL_操作},
        "require": {"ID", "车牌", "车型", "桩 ID", "命中规则", "命中时间",
                    "提醒状态", "提醒时间"},
    },
    "pile-status.html": {
        "table": "charging_pile",
        "allow": {"桩 ID", "状态", "绑定车牌", "开始充电时间", "充满时间", COL_操作},
        "require": {"桩 ID", "状态", "绑定车牌", "开始充电时间", "充满时间"},
    },
    "statistics.html": {
        "table": "occupation_record(下钻)",
        "allow": {"车牌", "车型", "桩 ID", "命中规则", "命中时间"},
        "require": {"车牌", "车型", "桩 ID", "命中规则", "命中时间"},
    },
    "system-config.html": {
        "table": "system_config",
        "allow": {"参数键", "参数值", "说明", COL_操作},
        "require": {"参数键", "参数值", "说明"},
    },
}

# 同一张表被多页引用时，同一个契约字段必须用同一个列名写法。
# 反例（2026-09-19 终检发现）：第 2 页写「车牌号」而第 4 页写「车牌」，
# 两页读的是同一张 occupation_record，用户在页间要重新认一遍列。
# 白名单挡不住这种错——因为白名单和线框出自同一手，必须单独交叉比对。
SHARED_TABLE_PAGES = [
    ("occupation_record", "records.html", "statistics.html"),
]

NAV_ITEM_RE = re.compile(r"<a\b[^>]*class=\"nav-item[^\"]*\"[^>]*>.*?</a>", re.S)
TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
H1_RE = re.compile(r"<h1 class=\"page-title\">(.*?)</h1>", re.S)
# padding / margin / gap 里出现的裸 px（≥4px 即为脱离 4px 栅格的间距）
BARE_SPACING_RE = re.compile(r"\b(?:padding|margin|gap|row-gap|column-gap)"
                             r"(?:-[a-z]+)?\s*:\s*([^;{}]+)")
PX_RE = re.compile(r"(\d+(?:\.\d+)?)px")
MONO_RE = re.compile(r"class=\"[^\"]*\bmono\b")
# 间距栅格的最小裸值：<4px 视为描边/字内微调，不算间距
SPACING_MIN = 4


def strip_tags(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def nav_text(item):
    """从 .nav-item 里取纯文案：去掉序号块与预留角标。"""
    item = re.sub(r"<span class=\"nav-idx\">.*?</span>", "", item, flags=re.S)
    item = re.sub(r"<span class=\"nav-tag\">.*?</span>", "", item, flags=re.S)
    return strip_tags(item)


def check_consistency():
    print("=" * 78)
    print("[5] 跨页一致性（component-inventory.md §5 走查清单的可执行版）")
    print("=" * 78)

    if not os.path.isdir(WIREFRAME_DIR):
        warn("线框目录不存在：%s" % WIREFRAME_DIR)
        print("  跳过")
        print()
        return

    files = [f for f in sorted(os.listdir(WIREFRAME_DIR)) if f.lower().endswith((".html", ".htm"))]
    for f in files:
        if f not in CONTRACT_COLUMNS:
            warn("线框 %s 未登记契约字段白名单；新增页面须先改 CONTRACT.md §1.1 并登记到本脚本" % f)
    print("  已登记 %d 页，目录内共 %d 个线框" % (len(CONTRACT_COLUMNS), len(files)))
    print()

    for f in files:
        if f not in CONTRACT_COLUMNS:
            continue
        spec = CONTRACT_COLUMNS[f]
        text = open(os.path.join(WIREFRAME_DIR, f), encoding="utf-8").read()
        problems = []

        # --- 5.1 导航：顺序一致 + 当前页高亮 + 第 6 页预留 ---
        items = NAV_ITEM_RE.findall(text)
        texts = [nav_text(i) for i in items]
        if texts != NAV_ORDER:
            problems.append("导航 6 项与契约 §1.1 顺序不一致：%s" % " / ".join(texts))
        actives = [nav_text(i) for i in items if "is-active" in i]
        if len(actives) != 1:
            problems.append("应恰有 1 个当前页高亮（is-active），实际 %d 个" % len(actives))
        reserved = [i for i in items if "is-reserved" in i]
        if len(reserved) != 1 or nav_text(reserved[0]) != NAV_ORDER[-1]:
            problems.append("第 6 页「%s」应且仅应标记 is-reserved（第 1 周预留）" % NAV_ORDER[-1])

        titles = [strip_tags(t) for t in H1_RE.findall(text)]
        if len(titles) != 1:
            problems.append("应恰有 1 个页面标题（h1.page-title），实际 %d 个" % len(titles))
        elif actives and titles[0] != actives[0]:
            problems.append("页面标题「%s」与高亮的导航项「%s」不一致" % (titles[0], actives[0]))

        # --- 5.2 空态 ---
        if 'class="empty"' not in text:
            problems.append("缺少空态区块（class=\"empty\"）")

        # --- 5.3 表格统一规格 ---
        if not re.search(r"thead th\s*\{[^}]*background:\s*var\(--fill-light\)", text, re.S):
            problems.append("表头未使用 --fill-light 底色")
        if not re.search(r"tbody td\s*\{[^}]*border-bottom:\s*1px solid var\(--border-light\)", text, re.S):
            problems.append("表格行线未使用 --border-light")
        if not re.search(r"tr\.is-hover td\s*\{\s*background:\s*var\(--brand-primary-bg\)", text):
            problems.append("表格悬浮行未使用 --brand-primary-bg")

        # --- 5.4 定长标识用等宽字族 ---
        mono_count = len(MONO_RE.findall(text))
        if mono_count < 4:
            problems.append("等宽字族（.mono）使用过少（%d 处），车牌/桩 ID/时间应走等宽" % mono_count)

        # --- 5.5 表格列名 ⊆ 契约字段白名单，且关键列齐全 ---
        cols = [strip_tags(c) for c in TH_RE.findall(text)]
        unknown = [c for c in cols if c not in spec["allow"]]
        if unknown:
            problems.append("表格列名超出契约字段白名单（%s 表）：%s"
                            % (spec["table"], " / ".join(unknown)))
        missing = sorted(spec["require"] - set(cols))
        if missing:
            problems.append("缺少契约字段列（%s 表）：%s" % (spec["table"], " / ".join(missing)))

        # --- 5.6 间距只取 4px 栅格令牌 ---
        bare = []
        for value in BARE_SPACING_RE.findall(text):
            for px in PX_RE.findall(value):
                if float(px) >= SPACING_MIN:
                    bare.append("%spx" % px)
        if bare:
            problems.append("间距出现裸 px 值（应取 --space-* / --layout-*）：%s"
                            % ", ".join(sorted(set(bare))))

        print("  %s  （%s · 表格 %d 列 · 等宽 %d 处）" % (f, spec["table"], len(cols), mono_count))
        for p in problems:
            fail("%s：%s" % (f, p))
        if not problems:
            print("    导航 / 高亮 / 空态 / 表格规格 / 列名 / 间距  全部一致")
    print()

    # --- 5.7 同一张表被多页引用时，列名不得各写各的 ---
    for table, base, other in SHARED_TABLE_PAGES:
        pb = os.path.join(WIREFRAME_DIR, base)
        po = os.path.join(WIREFRAME_DIR, other)
        if not (os.path.isfile(pb) and os.path.isfile(po)):
            continue
        with open(pb, encoding="utf-8") as fh:
            cols_base = [strip_tags(c) for c in TH_RE.findall(fh.read())]
        with open(po, encoding="utf-8") as fh:
            cols_other = [strip_tags(c) for c in TH_RE.findall(fh.read())]
        diverged = [c for c in cols_other if c not in cols_base]
        print("  同表跨页列名（%s）：%s ⊆ %s → %s"
              % (table, other, base, "一致" if not diverged else "有分叉"))
        if diverged:
            fail("%s 与 %s 同读 %s 表，列名分叉：%s 出现「%s」，%s 里没有同名写法"
                 % (other, base, table, other, " / ".join(diverged), base))
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
    check_consistency()

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
