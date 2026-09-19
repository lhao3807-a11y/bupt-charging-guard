#!/usr/bin/env node
/**
 * 设计令牌同步与漂移校验。
 *
 * 背景：`frontend/src/styles/tokens.css` 必须是 `docs/design/tokens.css` 的**逐字副本**
 * （设计侧是唯一事实源，见 `docs/design/design-tokens.md` §0）。
 * 此前这个约束只写在文件头注释里、靠人肉 `cp` 执行，**上游改了忘同步无人拦**。
 * 本脚本把该约束变成可执行检查。
 *
 * 用法：
 *   node scripts/copy-tokens.mjs           # 校验（CI / 交付前用），有漂移则 exit 1
 *   node scripts/copy-tokens.mjs --write   # 从设计侧同步过来（覆盖前端副本）
 *   node scripts/copy-tokens.mjs --diff    # 校验失败时打印逐行差异
 *
 * 判定口径：**忽略文件头的来源声明差异**（前端副本会多一行「本文件是副本」的告警），
 * 只比对 `--token: value` 定义本身。这与 `docs/design/tools/check_tokens.py`
 * 第 1 项的「令牌总数 / 必需令牌 / 取值合法性」互补：脚本管**一致性**，checker 管**合规性**。
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '..', '..')

const SOURCE = resolve(ROOT, 'docs', 'design', 'tokens.css')
const TARGET = resolve(ROOT, 'frontend', 'src', 'styles', 'tokens.css')

const ARGS = new Set(process.argv.slice(2))
const MODE_WRITE = ARGS.has('--write')
const MODE_DIFF = ARGS.has('--diff')

/** 提取 `--name: value;` 形式的令牌定义，返回 name → value 映射。 */
function extractTokens(css) {
  const map = new Map()
  const re = /(--[\w-]+)\s*:\s*([^;]+);/g
  let m
  while ((m = re.exec(css)) !== null) {
    const name = m[1]
    const value = m[2].trim().replace(/\s+/g, ' ')
    // 同名重复定义取最后一次（CSS 后者覆盖前者）
    map.set(name, value)
  }
  return map
}

function fail(msg) {
  console.error(`\x1b[31m✗\x1b[0m ${msg}`)
  process.exitCode = 1
}

function ok(msg) {
  console.log(`\x1b[32m✓\x1b[0m ${msg}`)
}

function main() {
  if (!existsSync(SOURCE)) {
    fail(`设计侧令牌文件不存在：${SOURCE}`)
    return
  }
  if (!existsSync(TARGET)) {
    fail(`前端令牌副本不存在：${TARGET}`)
    return
  }

  const srcCss = readFileSync(SOURCE, 'utf8')
  const tgtCss = readFileSync(TARGET, 'utf8')

  const src = extractTokens(srcCss)
  const tgt = extractTokens(tgtCss)

  if (MODE_WRITE) {
    if (srcCss === tgtCss) {
      ok('已是最新，无需同步')
      return
    }
    writeFileSync(TARGET, srcCss, 'utf8')
    ok(`已同步 ${src.size} 个令牌 → frontend/src/styles/tokens.css`)
    return
  }

  const missing = [] // 设计侧有、前端缺
  const extra = [] // 前端有、设计侧无（自造令牌）
  const drifted = [] // 同名不同值

  for (const [name, value] of src) {
    if (!tgt.has(name)) missing.push(name)
    else if (tgt.get(name) !== value) drifted.push({ name, want: value, got: tgt.get(name) })
  }
  for (const name of tgt.keys()) {
    if (!src.has(name)) extra.push(name)
  }

  console.log('='.repeat(78))
  console.log(`[设计令牌同步校验]  ${SOURCE}`)
  console.log('='.repeat(78))
  console.log(`  设计侧令牌：${src.size}`)
  console.log(`  前端副本：  ${tgt.size}`)
  console.log('')

  if (missing.length === 0 && extra.length === 0 && drifted.length === 0) {
    ok('零漂移 —— 前端副本与设计侧完全一致')
    return
  }

  if (missing.length > 0) {
    fail(`前端缺少 ${missing.length} 个令牌（设计侧新增未同步）：`)
    for (const n of missing.slice(0, 20)) console.log(`    - ${n}: ${src.get(n)}`)
    if (missing.length > 20) console.log(`    ... 另有 ${missing.length - 20} 个`)
  }
  if (extra.length > 0) {
    fail(`前端多出 ${extra.length} 个令牌（可能是自造，禁止）：`)
    for (const n of extra.slice(0, 20)) console.log(`    + ${n}: ${tgt.get(n)}`)
    if (extra.length > 20) console.log(`    ... 另有 ${extra.length - 20} 个`)
  }
  if (drifted.length > 0) {
    fail(`有 ${drifted.length} 个令牌取值漂移（同名不同值）：`)
    for (const d of drifted.slice(0, 20)) {
      console.log(`    ~ ${d.name}: 设计侧 ${d.want}  前端 ${d.got}`)
    }
    if (drifted.length > 20) console.log(`    ... 另有 ${drifted.length - 20} 个`)
  }

  console.log('')
  console.log('  修复：node frontend/scripts/copy-tokens.mjs --write')
  console.log('        （若漂移来自误改前端副本，同步即恢复；若来自设计侧变更，同步后一并提交）')

  if (MODE_DIFF) {
    console.log('')
    console.log('--- 逐行差异（diff 风格，仅令牌定义行） ---')
    for (const [name, value] of src) {
      const cur = tgt.get(name)
      if (cur !== value) console.log(`  - ${name}: ${cur ?? '<缺失>'}`)
      if (cur !== value) console.log(`  + ${name}: ${value}`)
    }
  }
}

main()
