# -*- coding: utf-8 -*-
"""通用文档排版脚本（Stage 2 doc-typeset 执行器）：把 Standard Markdown 渲染为 business-report 版式 HTML。
用法：python scripts/build_doc_html.py <input.md> <output.html>
模板与 CSS 来自 tencent-docx 插件 business-modern 主题，已通过 html-review score 100。
注意：空行不得产出空 <p>（触发 TQ-02）；每个 <h2> 后必须有导语段再进 <h3>（触发 TQ-03）。"""
import html
import re
import sys

SRC, OUT = sys.argv[1], sys.argv[2]

CSS_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="docx-page-size" content="A4">
  <title>「桩」点北邮 · 充电桩车位防占系统 · 商业计划书</title>
  <style>
  @page { @bottom-center { content: counter(page); } }
  @page cover { @bottom-center { content: none; } }
  section[role="cover"] { page: cover; }

  :root {
    /* ---- design tokens: business-modern（来自 doc-design-token 预编译产物） ---- */
    --typography-fontFamily-heading: 微软雅黑, Microsoft YaHei, PingFang SC;
    --typography-fontFamily-body: 微软雅黑, Microsoft YaHei, PingFang SC;
    --typography-fontFamily-bodyLatin: Calibri, Helvetica Neue, sans-serif;
    --typography-fontFamily-data: DIN Next, Arial, sans-serif;
    --typography-fontFamily-mono: Consolas, Source Code Pro, monospace;
    --typography-fontSize-title: 28pt;
    --typography-fontSize-subtitle: 18pt;
    --typography-fontSize-h1: 20pt;
    --typography-fontSize-coverTitle: 22pt;
    --typography-fontSize-coverCategory: 14pt;
    --typography-fontSize-sectionHeader: 13pt;
    --typography-fontSize-h2: 13pt;
    --typography-fontSize-h3: 11pt;
    --typography-fontSize-body: 10pt;
    --typography-fontSize-small: 8pt;
    --typography-fontSize-tiny: 7pt;
    --typography-lineHeight-title: 1.3;
    --typography-lineHeight-body: 1.6;
    --typography-lineHeight-compact: 1.25;
    --typography-fontWeight-heading: 600;
    --typography-fontWeight-bold: 700;
    --typography-fontWeight-body: 400;
    --color-primary: #1565C0;
    --color-secondary: #0288D1;
    --color-accent: #00897B;
    --color-text: #212121;
    --color-textSecondary: #616161;
    --color-heading: #1A237E;
    --color-divider: #E0E0E0;
    --color-background: #FFFFFF;
    --color-surface: #F5F7FA;
    --color-danger: #E53935;
    --color-warning: #E65100;
    --color-success: #2E7D32;
    --spacing-paragraph: 0.6em;
    --spacing-sectionGap: 2.0em;
    --spacing-cardPadding: 1.2em;
    --layout-marginTop: 2.5cm;
    --layout-marginBottom: 2.0cm;
    --layout-marginLeft: 2.5cm;
    --layout-marginRight: 2.5cm;
    --layout-pageSize: A4;
    --layout-contentWidth: 16.0cm;

    /* ---- 本地别名（供样式引用；DT 检查的必需变量在此块内） ---- */
    --fs-title: var(--typography-fontSize-title);
    --fs-subtitle: var(--typography-fontSize-subtitle);
    --fs-h1: var(--typography-fontSize-h1);
    --fs-cover-title: var(--typography-fontSize-coverTitle);
    --fs-cover-category: var(--typography-fontSize-coverCategory);
    --fs-h2: var(--typography-fontSize-h2);
    --fs-h3: var(--typography-fontSize-h3);
    --fs-body: var(--typography-fontSize-body);
    --fs-small: var(--typography-fontSize-small);
    --fs-tiny: var(--typography-fontSize-tiny);
    --ff-heading: var(--typography-fontFamily-heading);
    --ff-body: var(--typography-fontFamily-body);
    --ff-mono: var(--typography-fontFamily-mono);
    --ff-data: var(--typography-fontFamily-data);
    --lh-body: var(--typography-lineHeight-body);
    --lh-tight: var(--typography-lineHeight-compact);
    --fw-bold: var(--typography-fontWeight-bold);
    --fw-normal: var(--typography-fontWeight-body);
    --color-bg: var(--color-background);
    --color-border: var(--color-divider);
    --color-muted: var(--color-textSecondary);
    --color-highlight: var(--color-surface);
    --color-emphasis: var(--color-danger);
    --color-note-bg: #EAF1FB;
    --color-note-border: #1565C0;
    --color-table-head-bg: #EAF1FB;
    --color-table-zebra: #F7F9FC;

    /* ---- 尺寸/间距字面量（统一在 -- 变量中定义，声明处一律 var() 引用） ---- */
    --page-content-width: var(--layout-contentWidth);
    --space-cell-y: 0.42em;
    --space-cell-x: 0.62em;
    --space-block: 0.9em;
    --space-section: 1.8em;
    --space-toc-indent: 1.4em;
    --space-toc-gap: 0.28em;
    --space-meta-gap: 0.3em;
    --space-cover-lead: 0.6em;
    --space-cover-tail: 2.4em;
    --space-rule-y: 1.1em;
    --rule-width: 4px;
    --radius-card: 3px;
    --cover-min-height: 16cm;
    --toc-rule: 1px solid;
    --tbl-rule: 1px solid;
    --border-hair: 0px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--ff-body);
    font-size: var(--fs-body);
    line-height: var(--lh-body);
    color: var(--color-text);
    background: var(--color-bg);
    max-width: var(--page-content-width);
    margin-left: auto;
    margin-right: auto;
  }

  /* ---------- 封面 ---------- */
  section[role="cover"] {
    min-height: var(--cover-min-height);
    padding-top: var(--space-cover-tail);
    padding-bottom: var(--space-cover-tail);
    border-bottom: var(--rule-width) solid var(--color-primary);
    margin-bottom: var(--space-section);
  }
  p.cover-category {
    text-align: center;
    font-family: var(--ff-heading);
    font-size: var(--fs-cover-category);
    font-weight: var(--fw-bold);
    color: var(--color-primary);
    letter-spacing: 0.10em;
    margin-bottom: var(--space-cover-lead);
  }
  h1.cover-title {
    text-align: center;
    font-family: var(--ff-heading);
    font-size: var(--fs-cover-title);
    font-weight: var(--fw-bold);
    color: var(--color-heading);
    line-height: var(--lh-tight);
    margin-bottom: var(--space-cover-lead);
  }
  p.cover-subtitle {
    text-align: center;
    font-family: var(--ff-heading);
    font-size: var(--fs-subtitle);
    font-weight: var(--fw-normal);
    color: var(--color-text);
    line-height: var(--lh-tight);
    margin-bottom: var(--space-cover-lead);
  }
  p.cover-subtitle-en {
    text-align: center;
    font-family: var(--ff-data);
    font-size: var(--fs-small);
    color: var(--color-muted);
    letter-spacing: 0.04em;
    margin-bottom: var(--space-cover-tail);
  }
  p.cover-meta {
    text-align: center;
    font-size: var(--fs-small);
    color: var(--color-text);
    line-height: var(--lh-body);
    margin-bottom: var(--space-meta-gap);
  }
  p.cover-meta-key {
    text-align: center;
    font-size: var(--fs-tiny);
    color: var(--color-muted);
    line-height: var(--lh-body);
    margin-top: var(--space-block);
  }

  /* ---------- 目录 ---------- */
  nav.doc-toc {
    background: var(--color-highlight);
    padding: var(--space-block);
    margin-bottom: var(--space-section);
    border-left: var(--rule-width) solid var(--color-primary);
  }
  p.toc-title {
    font-family: var(--ff-heading);
    font-size: var(--fs-h3);
    font-weight: var(--fw-bold);
    color: var(--color-heading);
    margin-bottom: var(--space-toc-gap);
  }
  ol.toc-list { list-style: none; list-style-type: none; padding-left: var(--space-toc-indent); }
  ol.toc-list li { margin-bottom: var(--space-toc-gap); font-size: var(--fs-body); }
  ol.toc-list a { color: var(--color-primary); text-decoration: none; }

  /* ---------- 执行摘要 ---------- */
  div.executive-summary {
    background: var(--color-highlight);
    padding: var(--space-block);
    margin-bottom: var(--space-section);
    border-left: var(--rule-width) solid var(--color-primary);
  }
  div.executive-summary h2 {
    font-family: var(--ff-heading);
    font-size: var(--fs-h2);
    font-weight: var(--fw-bold);
    color: var(--color-heading);
    margin-bottom: var(--space-toc-gap);
  }
  p.summary-badge {
    font-family: var(--ff-data);
    font-size: var(--fs-tiny);
    color: var(--color-muted);
    letter-spacing: 0.06em;
    margin-bottom: var(--space-block);
  }

  /* ---------- 正文 ---------- */
  h2 {
    font-family: var(--ff-heading);
    font-size: var(--fs-h2);
    font-weight: var(--fw-bold);
    color: var(--color-heading);
    line-height: var(--lh-tight);
    margin-top: var(--space-section);
    margin-bottom: var(--space-paragraph);
    padding-bottom: var(--space-toc-gap);
    border-bottom: var(--rule-width) solid var(--color-primary);
  }
  h3 {
    font-family: var(--ff-heading);
    font-size: var(--fs-h3);
    font-weight: var(--fw-bold);
    color: var(--color-primary);
    line-height: var(--lh-tight);
    margin-top: var(--space-block);
    margin-bottom: var(--space-paragraph);
  }
  p { font-size: var(--fs-body); margin-bottom: var(--space-paragraph); text-align: justify; }
  ul, ol { margin-bottom: var(--space-paragraph); padding-left: var(--space-toc-indent); }
  li { font-size: var(--fs-body); margin-bottom: var(--space-meta-gap); text-align: justify; }
  strong { font-weight: var(--fw-bold); }
  code {
    font-family: var(--ff-mono);
    font-size: var(--fs-small);
    color: var(--color-primary);
  }
  span.data-emphasis { color: var(--color-emphasis); font-weight: var(--fw-bold); }

  /* 提示段（单段强调，docx 可还原为 w:pBdr / w:shd） */
  p.note {
    background: var(--color-note-bg);
    border-left: var(--rule-width) solid var(--color-note-border);
    padding: var(--space-cell-y) var(--space-cell-x);
    margin-top: var(--space-rule-y);
    margin-bottom: var(--space-rule-y);
  }
  p.flow {
    background: var(--color-highlight);
    padding: var(--space-cell-y) var(--space-cell-x);
    line-height: var(--lh-tight);
    margin-bottom: var(--space-paragraph);
  }

  /* ---------- 表格 ---------- */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: var(--space-block);
  }
  caption {
    font-family: var(--ff-heading);
    font-size: var(--fs-small);
    font-weight: var(--fw-bold);
    color: var(--color-muted);
    text-align: left;
    margin-bottom: var(--space-meta-gap);
  }
  th {
    font-family: var(--ff-heading);
    font-size: var(--fs-small);
    font-weight: var(--fw-bold);
    color: var(--color-heading);
    background: var(--color-table-head-bg);
    border: var(--tbl-rule) var(--color-border);
    padding: var(--space-cell-y) var(--space-cell-x);
    text-align: left;
    vertical-align: middle;
  }
  td {
    font-size: var(--fs-small);
    color: var(--color-text);
    border: var(--tbl-rule) var(--color-border);
    padding: var(--space-cell-y) var(--space-cell-x);
    text-align: left;
    vertical-align: top;
    line-height: var(--lh-tight);
  }
  table.kv-table td:first-child { width: 30%; }
  table.kv-table td { vertical-align: middle; }
  table.metrics th, table.metrics td { text-align: center; }
  table.metrics th:first-child, table.metrics td:first-child { text-align: left; }
  </style>
</head>
<body>
"""


def inline(text):
    """转义 + 行内标记（code / strong）"""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    for i, c in enumerate(codes):
        text = text.replace("\x00%d\x00" % i, "<code>" + html.escape(c, quote=False) + "</code>")
    return text


def cells(line):
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def main():
    raw = open(SRC, encoding="utf-8").read().splitlines()

    # ---- 元信息与正文切分 ----
    # 首个 "## " 之前为封面元信息区（标题行 + 引用块 + 分隔线），只用于封面，不进正文；
    # 首个 "## " 之后，引用块是正文里的提示段，必须保留。
    first_h2 = next((k for k, l in enumerate(raw) if l.startswith("## ")), len(raw))
    lines = []
    for k, ln in enumerate(raw):
        if k < first_h2:
            continue
        if ln.strip() in ("---", ""):
            lines.append("")
            continue
        lines.append(ln)

    # ---- 目录 ----
    h2s = [l[3:].strip() for l in lines if l.startswith("## ")]
    toc = "\n".join(
        '        <li><a href="#section-%d">%s</a></li>' % (i + 1, inline(t))
        for i, t in enumerate(h2s)
    )

    # ---- 正文渲染 ----
    body = []
    i = 0
    h2_idx = 0
    in_metrics = False
    n = len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()

        if not s:            # 空行只用于分隔，不产出空 <p>（否则触发 TQ-02）
            i += 1
            continue

        if s.startswith("## "):
            h2_idx += 1
            title = s[3:].strip()
            in_metrics = "技术指标" in title
            body.append('      <h2 id="section-%d">%s</h2>' % (h2_idx, inline(title)))
            i += 1
            continue

        if s.startswith("### "):
            body.append("      <h3>%s</h3>" % inline(s[4:].strip()))
            i += 1
            continue

        # 代码块 -> 流程图
        if s.startswith("```"):
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i].rstrip())
                i += 1
            i += 1
            body.append('      <p class="flow">%s</p>' % "<br>".join(inline(b) for b in block))
            continue

        # 表格
        if s.startswith("|"):
            header = cells(lines[i])
            i += 2  # 跳过表头分隔行
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            cls = ' class="metrics"' if in_metrics else ""
            buf = ["      <table%s>" % cls, "        <thead>", "          <tr>"]
            buf += ["            <th>%s</th>" % inline(h) for h in header]
            buf += ["          </tr>", "        </thead>", "        <tbody>"]
            for r in rows:
                buf.append("          <tr>")
                buf += ["            <td>%s</td>" % inline(c) for c in r]
                buf.append("          </tr>")
            buf += ["        </tbody>", "      </table>"]
            body.append("\n".join(buf))
            continue

        # 引用 -> 提示段
        if s.startswith(">"):
            body.append('      <p class="note">%s</p>' % inline(s.lstrip("> ").strip()))
            i += 1
            continue

        # 无序列表
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            buf = ["      <ul>"]
            buf += ["        <li>%s</li>" % inline(x) for x in items]
            buf += ["      </ul>"]
            body.append("\n".join(buf))
            continue

        # 有序列表
        if re.match(r"^\d+\.\s", s):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s", "", lines[i].strip()))
                i += 1
            buf = ["      <ol>"]
            buf += ["        <li>%s</li>" % inline(x) for x in items]
            buf += ["      </ol>"]
            body.append("\n".join(buf))
            continue

        # 普通段落
        body.append("      <p>%s</p>" % inline(s))
        i += 1

    cover = """  <section role="cover">
    <p class="cover-category">大学生创新创业竞赛 · 创新训练类</p>
    <h1 class="cover-title">「桩」点北邮</h1>
    <p class="cover-subtitle">充电桩车位防占系统 · 商业计划书</p>
    <p class="cover-subtitle-en">BUPT Charging Guard — EV Parking Anti-Occupation System</p>
    <p class="cover-meta">团队负责人：吕浩（2024210416）　　指导教师：景文鹏（副教授）</p>
    <p class="cover-meta">团队成员：吕浩 · 汤瑾睿 · 吴和庆</p>
    <p class="cover-meta">依托单位：北京邮电大学 信息与通信工程学院</p>
    <p class="cover-meta">文档版本：v1.0　|　编制日期：2026-09-14　|　数据截止：2026 年 6 月</p>
    <p class="cover-meta-key">依据文件：立项申请书、开发大纲、设计文档、docs/CONTRACT.md v1.2、docs/PLAN_4WEEKS.md v1.0</p>
  </section>"""

    summary = """    <div class="executive-summary">
      <h2>执行摘要</h2>
      <p class="summary-badge">EXECUTIVE SUMMARY</p>
      <table class="kv-table">
        <thead>
          <tr><th>项目概况</th><th>内容</th></tr>
        </thead>
        <tbody>
          <tr><td>项目全称</td><td>「桩」点北邮——充电桩车位防占系统</td></tr>
          <tr><td>英文名称</td><td>BUPT Charging Guard: EV Parking Anti-Occupation System</td></tr>
          <tr><td>参赛类别</td><td>大学生创新创业竞赛 · 创新训练类</td></tr>
          <tr><td>依托单位</td><td>北京邮电大学 信息与通信工程学院</td></tr>
          <tr><td>团队负责人</td><td>吕浩（2024210416）</td></tr>
          <tr><td>指导教师</td><td>景文鹏（副教授）</td></tr>
          <tr><td>团队成员</td><td>吕浩（统筹 / 集成 / 前端）、汤瑾睿（后端 / 数据库 / 算法）、吴和庆（UI / 美术）</td></tr>
          <tr><td>产品形态</td><td>软件为主、硬件可选的充电车位智能监管系统（识别 + 判断 + 提醒 + 留痕）</td></tr>
          <tr><td>客户对象</td><td>高校后勤与充电设施管理部门、党政机关与公立医院等公共机构、园区写字楼运营方</td></tr>
          <tr><td>收入模式</td><td>平台部署费 + 按监管车位计费的年度授权费 + 短信通道费 + 可选增值模块</td></tr>
          <tr><td>三年目标</td><td>期末存量 41 个场站，第 3 年收入约 140.6 万元，经常性收入占比约 46.7%</td></tr>
        </tbody>
      </table>
      <p>「桩」点北邮面向高校与公共机构的充电车位管理，以「视觉识别 + 设备状态」融合判断的方式，识别燃油车占位、异常占位与新能源车充满未移车三类违规，命中即短信提醒车主并结构化落库，形成「识别—判断—提醒—留痕」的自动闭环。项目的立足点是：判定违规所必需的「充电状态」这一维度，只有与视觉识别联合才可获得，因此现有方案普遍无法识别「充满未移车」这类中间状态。政策层面，公共机构充电车位配建不低于总车位 25% 的行业标准自 2026 年 3 月起实施，需求正在成规模扩大。团队已完成接口契约、数据库四表与规则引擎、后端接口层，端到端闭环已打通，当前主线为管理后台与计算机视觉真实模型。</p>
    </div>"""

    out = [
        CSS_HEAD,
        cover,
        "",
        '  <section role="body" data-page-restart="1">',
        '    <nav class="doc-toc" aria-label="文档目录">',
        '      <p class="toc-title">目录</p>',
        '      <ol class="toc-list">',
        toc,
        "      </ol>",
        "    </nav>",
        "",
        summary,
        "",
        "    <main>",
        "\n".join(body),
        "    </main>",
        "  </section>",
        "</body>",
        "</html>",
        "",
    ]
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("H2 sections:", h2_idx)
    print("output:", OUT)


main()
