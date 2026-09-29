"""答辩演示截图工具 —— 「真实页面拍摄」+「统一设备框美化」（第 2 周任务 6.10）

为什么要有这个脚本
------------------------------------------------------------------------
任务书 6.10 要求「6 页系统截图美化（统一设备框、窗口标题、脱敏处理）」，
并明确 **截图须真实页面，不许用线框冒充**。

手工截图的问题不是慢，而是**不可复现**：谁拍的、什么视口、什么时间、
后来页面改了没有 —— 答辩前一周没人说得清。所以这里把两步都写成命令：

    python docs/design/tools/demo_screenshots.py            # 拍摄 + 美化
    python docs/design/tools/demo_screenshots.py --frame-only   # 只重做美化
    python docs/design/tools/demo_screenshots.py --shoot-only   # 只重拍

颜色一律从 `docs/design/tokens.css` **读**出来（不是抄进来），
所以设备框不会随令牌改版而变成过期配色 —— 同 `check_tokens.py` 的思路。

前置：后端 `uvicorn app.main:app --port 8000`、前端 `npm run dev` 已起。
本机浏览器用 Edge（Chromium 内核，同 Chrome 的无头截图参数）。

⚠️ 脱敏：手机号在页面里已由前端 `maskPhone` 处理（`138****6621`）；
   车牌是否脱敏口径未定（`walkthrough.md` §9.6 的 R9），脚本会在末尾提醒。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
TOKENS_CSS = ROOT / "docs" / "design" / "tokens.css"
DEMO_DIR = ROOT / "docs" / "design" / "demo"
RAW_DIR = DEMO_DIR / "screenshots" / "raw"
OUT_DIR = DEMO_DIR / "screenshots"

FRONTEND = "http://localhost:5173"
# 视口取 1600×880：宽度够放下 6 页的完整表格，高度刚好让三行数据 + 分页都在框内，
# 不留大片空白（1000 高时底部约 1/4 是空的，进 PPT 很难看）。
VIEWPORT = (1600, 880)

# 只拍「已真实实现」的页面。第 3/4/5/6 页在 main 上仍是占位路由
# （每个 16–25 行，内容为「开发中」），拍出来进不了答辩材料，
# 故不拍 —— 等页面落地后把它们加进这张表即可（这也是脚本存在的意义）。
PAGES: list[tuple[str, str, str, str]] = [
    ("p1-vehicle", "/vehicle", "① 车辆信息管理", "车辆信息管理 · 桩点北邮防占系统"),
    ("p2-records", "/records", "② 违规记录查询", "违规记录查询 · 桩点北邮防占系统"),
    ("login", "/login", "登录页（任务 6.6）", "登录 · 桩点北邮防占系统"),
]

BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

# 设备框几何（px）。只有这里允许出现裸数值：**页面里**才禁止裸值，
# 本脚本产出的是一张位图，没有可继承的 CSS 变量。
PAD = 40  # 画布留白
TITLEBAR_H = 36
DOT_R = 5
DOT_GAP = 18
CAPTION_H = 34


# --------------------------------------------------------------- 令牌读取


def read_tokens() -> dict[str, str]:
    """从 tokens.css 解析 `--name: value;`，返回 {name: value}（去掉 var() 引用项）。"""
    if not TOKENS_CSS.exists():
        sys.exit("找不到 %s" % TOKENS_CSS)
    css = TOKENS_CSS.read_text(encoding="utf-8")
    tokens = {}
    for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css):
        value = value.strip()
        if value.startswith("var("):
            continue
        tokens[name] = value
    return tokens


def rgb(hex_or_rgba: str) -> tuple[int, int, int]:
    s = hex_or_rgba.strip()
    m = re.match(r"#([0-9A-Fa-f]{6})", s)
    if not m:
        sys.exit("无法解析颜色：%s（只支持 #RRGGBB，设备框不需要带透明度）" % s)
    h = m.group(1)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# ------------------------------------------------------------------- 拍摄


def find_browser() -> str:
    for p in BROWSER_CANDIDATES:
        if Path(p).exists():
            return p
    sys.exit("未找到 Chrome / Edge，无法拍摄。可手工截图后放进 %s 再跑 --frame-only" % RAW_DIR)


def shoot(browser: str, name: str, route: str, profile: Path) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / ("%s.png" % name)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--user-data-dir=%s" % profile,
        "--window-size=%d,%d" % VIEWPORT,
        # SPA 的关键：不加虚拟时间预算，截图会早于懒加载路由组件就绪，
        # 结果是「骨架渲染了、内容区空白」——第 2 周真踩过这个坑。
        "--virtual-time-budget=8000",
        "--screenshot=%s" % target,
        FRONTEND + route,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not target.exists():
        sys.exit("拍摄失败：%s\n%s" % (route, (proc.stderr or proc.stdout)[-800:]))
    print("  拍 %-14s %-28s → %s" % (name, route, target.relative_to(ROOT)))
    return target


# ------------------------------------------------------------------- 美化


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    print("  [警告] 未找到中文字体，标题会退化为系统默认字体（可能显示为方块）")
    return ImageFont.load_default(size)


def draw_window(src: Image.Image, title: str, caption: str, tk: dict[str, str]) -> Image.Image:
    bg_page = rgb(tk["--bg-page"])
    bg_card = rgb(tk["--bg-container"])
    border = rgb(tk["--border-base"])
    fill = rgb(tk["--fill-light"])
    strong = rgb(tk["--border-strong"])
    text_primary = rgb(tk["--text-primary"])
    text_secondary = rgb(tk["--text-secondary"])
    text_tertiary = rgb(tk["--text-tertiary"])

    shot_w, shot_h = src.size
    win_w = shot_w + 2  # 左右各 1px 边框
    win_h = TITLEBAR_H + shot_h + 2

    canvas_w = win_w + PAD * 2
    canvas_h = win_h + PAD * 2 + CAPTION_H
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_page)

    win_x, win_y = PAD, PAD

    # 阴影：先画一层半透明圆角块再高斯模糊，比 PIL 自带的 stroke 自然
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [win_x + 2, win_y + 6, win_x + win_w + 2, win_y + win_h + 6],
        radius=12,
        fill=(31, 35, 41, 46),
    )
    canvas.paste(
        Image.alpha_composite(
            canvas.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(8))
        ).convert("RGB"),
        (0, 0),
    )

    draw = ImageDraw.Draw(canvas)

    # 窗口本体
    draw.rounded_rectangle(
        [win_x, win_y, win_x + win_w, win_y + win_h], radius=10, fill=bg_card, outline=border
    )
    # 标题栏
    draw.rounded_rectangle(
        [win_x + 1, win_y + 1, win_x + win_w - 1, win_y + TITLEBAR_H],
        radius=10,
        fill=fill,
    )
    draw.rectangle(
        [win_x + 1, win_y + TITLEBAR_H - 12, win_x + win_w - 1, win_y + TITLEBAR_H - 1],
        fill=fill,
    )
    draw.line(
        [win_x + 1, win_y + TITLEBAR_H, win_x + win_w - 1, win_y + TITLEBAR_H], fill=border
    )

    # 三个圆点：**故意用中性色**（--border-strong），不套 danger/caution/success。
    # 本项目里红/橙/黄/绿是「违规严重度」的语义色，拿去做装饰会和状态色语义打架。
    cy = win_y + TITLEBAR_H // 2
    for i in range(3):
        cx = win_x + 16 + i * DOT_GAP
        draw.ellipse([cx - DOT_R, cy - DOT_R, cx + DOT_R, cy + DOT_R], fill=strong)

    # 窗口标题（左侧对齐，标题即「页面名 · 系统名」，与浏览器标签页一致）
    font_title = load_font(13)
    draw.text(
        (win_x + 16 + 2 * DOT_GAP + 8, cy),
        title,
        font=font_title,
        fill=text_secondary,
        anchor="lm",
    )

    # 页面本体
    canvas.paste(src, (win_x + 1, win_y + TITLEBAR_H + 1))

    # 图注：左「序号 + 页面名」，右「品牌 + 演示原型」
    font_cap = load_font(13)
    cap_y = win_y + win_h + 10
    draw.text((win_x + 2, cap_y), caption, font=font_cap, fill=text_primary, anchor="la")
    draw.text(
        (win_x + win_w - 2, cap_y),
        "「桩」点北邮 · 充电桩车位防占系统 · 演示原型",
        font=font_cap,
        fill=text_tertiary,
        anchor="ra",
    )
    return canvas


# -------------------------------------------------------------------- 主流程


def main() -> int:
    ap = argparse.ArgumentParser(description="答辩演示截图：拍摄 + 设备框美化")
    ap.add_argument("--shoot-only", action="store_true", help="只拍原始图")
    ap.add_argument("--frame-only", action="store_true", help="只做美化（用已有原始图）")
    args = ap.parse_args()

    tk = read_tokens()
    for need in ("--bg-page", "--bg-container", "--border-base", "--fill-light",
                 "--border-strong", "--text-primary", "--text-secondary", "--text-tertiary"):
        if need not in tk:
            sys.exit("tokens.css 缺令牌 %s（设备框取色依赖它）" % need)

    profile = RAW_DIR.parent / "_profile"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.frame_only:
        browser = find_browser()
        print("[1/2] 拍摄真实页面（%s，视口 %dx%d）" % (Path(browser).name, *VIEWPORT))
        try:
            for name, route, _caption, _title in PAGES:
                shoot(browser, name, route, profile)
        finally:
            shutil.rmtree(profile, ignore_errors=True)

    if not args.shoot_only:
        print("[2/2] 套统一设备框（取色自 tokens.css）")
        for name, _route, caption, title in PAGES:
            src_path = RAW_DIR / ("%s.png" % name)
            if not src_path.exists():
                print("  [跳过] 缺原始图 %s" % src_path.relative_to(ROOT))
                continue
            out = draw_window(Image.open(src_path).convert("RGB"), title, caption, tk)
            dst = OUT_DIR / ("%s-framed.png" % name)
            out.save(dst)
            print("  框 %-14s %dx%d → %s" % (name, *out.size, dst.relative_to(ROOT)))

    print("\n完成。输出目录：%s" % OUT_DIR.relative_to(ROOT))
    print("提醒：手机号已由页面 maskPhone 脱敏；**车牌是否脱敏**口径未定，见 walkthrough.md §9.6 的 R9。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
