"""MySQL 8 真机验证（PLAN 任务 5.6）。

**为什么需要这个脚本**：``backend/sql/schema.sql`` 是正式交付物、语法基线是 MySQL 8，
但开发期一直在 SQLite 上跑。SQLite 有几件事和 MySQL 8 不一样，光看代码看不出来：

- **外键**：SQLite 默认根本不启用外键约束（``PRAGMA foreign_keys`` 默认 OFF），
  所以 ``ON DELETE SET NULL`` 在 SQLite 上**可能压根没生效过**，而测试照样绿。
  MySQL 8 + InnoDB 会真的执行 —— 这正是必须上真机验的原因。
- **ENUM**：SQLite 没有原生 ENUM，SQLAlchemy 侧退化成 VARCHAR + CHECK；
  非法值是否被拒，两边行为不同。
- **DATETIME**：SQLite 存字符串，MySQL 8 是原生 DATETIME；时区与精度行为不同。
- **保留字**：``system_config.`key``` 的反引号转义是 MySQL 专有语法。

用法
----
挑一个 MySQL 驱动装上（脚本会自己找）::

    pip install pymysql            # 推荐，纯 Python
    pip install mysql-connector-python

然后::

    set MYSQL_HOST=127.0.0.1
    set MYSQL_PORT=3306
    set MYSQL_USER=root
    set MYSQL_PASSWORD=xxxx
    set MYSQL_DB=bupt_charging_guard
    .venv\\Scripts\\python.exe scripts\\verify_mysql.py

退出码 **0** = 全部通过，**1** = 有 FAIL（报告里会列出每一项的 PASS/FAIL 与原因）。
加 ``--json <路径>`` 可把结果存成验收凭据。

⚠️ 脚本会 **DROP 并重建** ``MYSQL_DB`` 库里的四张表（schema.sql 自带 DROP），
**不要指向有数据的库**。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
SCHEMA_SQL = os.path.join(REPO, "backend", "sql", "schema.sql")

#: 期望的四张表与存储引擎（契约 §3）
EXPECTED_TABLES = ("vehicle", "charging_pile", "occupation_record", "system_config")


def load_driver():
    """依次尝试 pymysql / mysql-connector-python / MySQLdb，都没有就给出安装指引。"""
    for name, mod in (
        ("pymysql", "pymysql"),
        ("mysql-connector-python", "mysql.connector"),
        ("mysqlclient", "MySQLdb"),
    ):
        try:
            return __import__(mod), name
        except ImportError:
            continue
    raise SystemExit(
        "没有可用的 MySQL 驱动。装一个再跑：\n"
        "  .venv\\Scripts\\python.exe -m pip install pymysql\n"
        "（或 mysql-connector-python / mysqlclient）"
    )


def split_statements(sql: str) -> list[str]:
    """把 schema.sql 拆成单条语句。

    朴素按 ``;`` 切分并去掉 ``--`` 注释：本项目的 schema.sql 里字符串常量不含分号，
    够用；若以后加了含分号的默认值/注释，需要换成真正的 SQL 解析器。
    """
    out = []
    for raw in sql.splitlines():
        line = raw.split("--")[0].strip() if not raw.strip().startswith("--") else ""
        if line:
            out.append(line)
    body = "\n".join(out)
    return [s.strip() for s in body.split(";") if s.strip()]


class Checker:
    """收集 PASS/FAIL，避免一处断言抛异常就看不到后面的结果。"""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" —— {detail}" if detail else ""))
        return bool(ok)

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.rows if not r["ok"]]


def run(conn) -> Checker:
    ck = Checker()
    cur = conn.cursor()

    # 1. 版本
    cur.execute("SELECT VERSION()")
    version = cur.fetchone()[0]
    ck.check("MySQL 版本为 8.x", version.startswith("8."), f"VERSION()={version}")

    cur.execute("SELECT @@sql_mode")
    sql_mode = cur.fetchone()[0] or ""
    strict = "STRICT_TRANS_TABLES" in sql_mode or "STRICT_ALL_TABLES" in sql_mode
    print(f"  INFO  sql_mode={sql_mode or '(空)'}（严格模式={strict}）")

    # 2. 建表
    with open(SCHEMA_SQL, encoding="utf-8") as fh:
        statements = split_statements(fh.read())
    for stmt in statements:
        try:
            cur.execute(stmt)
        except Exception as exc:  # noqa: BLE001 逐条执行，坏语句要报出来而不是整批中断
            ck.check(f"执行 SQL：{stmt[:60]}...", False, f"{type(exc).__name__}: {exc}")
    conn.commit()

    # 3. 四张表 + 引擎 + 字符集
    cur.execute(
        "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )
    tables = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    for t in EXPECTED_TABLES:
        info = tables.get(t)
        ck.check(f"表 {t} 存在且 ENGINE=InnoDB", bool(info) and info[0] == "InnoDB", str(info))
        if info:
            ck.check(f"表 {t} 字符集 utf8mb4", "utf8mb4" in (info[1] or ""), info[1])

    # 4. ENUM 列
    cur.execute(
        "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'charging_pile' AND COLUMN_NAME = 'status'"
    )
    row = cur.fetchone()
    ck.check(
        "charging_pile.status 是原生 ENUM",
        bool(row) and row[1].upper().startswith("ENUM"),
        str(row[1]) if row else "未查到",
    )

    # 4b. ENUM 非法值必须被拒（非严格模式下 MySQL 会存成空串，也算"没吃进去"）
    rejected = False
    detail = ""
    try:
        cur.execute("INSERT INTO charging_pile (pile_id, status) VALUES ('BAD-001', '不存在')")
        conn.commit()
        cur.execute("SELECT status FROM charging_pile WHERE pile_id = 'BAD-001'")
        got = cur.fetchone()
        rejected = got is None or got[0] not in ("不存在",)
        detail = f"实际存下 {got!r}（非严格模式会存成空串/0）" if got else ""
        cur.execute("DELETE FROM charging_pile WHERE pile_id = 'BAD-001'")
        conn.commit()
    except Exception as exc:  # noqa: BLE001 严格模式会抛，正是期望结果
        rejected, detail = True, f"被拒（{type(exc).__name__}）"
        conn.rollback()
    ck.check("ENUM 非法值不被接受", rejected, detail)

    # 5. 外键 ON DELETE SET NULL —— SQLite 默认不启用外键，这条最容易漏
    cur.execute("INSERT INTO vehicle (plate, vtype) VALUES ('京TEST01', '燃油')")
    cur.execute("INSERT INTO charging_pile (pile_id, bound_plate) VALUES ('PILE-TEST', '京TEST01')")
    conn.commit()
    cur.execute("DELETE FROM vehicle WHERE plate = '京TEST01'")
    conn.commit()
    cur.execute("SELECT bound_plate FROM charging_pile WHERE pile_id = 'PILE-TEST'")
    row = cur.fetchone()
    ck.check(
        "FK ON DELETE SET NULL 真的把 bound_plate 置空",
        row is not None and row[0] is None,
        f"删除车辆后 bound_plate={row[0] if row else '(行没了)'}",
    )
    cur.execute("DELETE FROM charging_pile WHERE pile_id = 'PILE-TEST'")
    conn.commit()

    # 6. occupation_record.plate 永久不加 FK（契约规定：记录要能留存已删车辆的历史）
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'occupation_record' "
        "AND COLUMN_NAME = 'plate' AND REFERENCED_TABLE_NAME IS NOT NULL"
    )
    ck.check("occupation_record.plate 未加外键", cur.fetchone()[0] == 0)

    # 7. DATETIME 往返一致（无时区、到秒）
    cur.execute(
        "INSERT INTO occupation_record (plate, vtype, rule_hit, occur_time) "
        "VALUES ('京TEST01', '燃油', 1, '2026-09-08 10:00:00')"
    )
    conn.commit()
    cur.execute("SELECT occur_time FROM occupation_record WHERE plate = '京TEST01'")
    got = cur.fetchone()[0]
    ck.check(
        "DATETIME 存取往返一致（无时区）",
        str(got) == "2026-09-08 10:00:00",
        f"读出 {got!r}",
    )
    cur.execute("DELETE FROM occupation_record WHERE plate = '京TEST01'")
    conn.commit()

    # 8. AUTO_INCREMENT
    # 走 information_schema 而不是 `SHOW TABLE STATUS`：后者返回 18 列，
    # 靠下标 [10] 取 AUTO_INCREMENT 太脆，不同驱动/版本列数还可能变。
    cur.execute(
        "SELECT AUTO_INCREMENT FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'occupation_record'"
    )
    auto_inc = cur.fetchone()[0]
    ck.check(
        "occupation_record.id 自增",
        auto_inc is not None and auto_inc >= 1,
        f"AUTO_INCREMENT={auto_inc}",
    )

    # 9. system_config 保留字 `key` 可正常读写
    cur.execute("SELECT `value` FROM system_config WHERE `key` = 'full_timeout_min'")
    row = cur.fetchone()
    ck.check(
        "system_config.`key` 反引号转义可用",
        row is not None,
        f"full_timeout_min={row[0] if row else None}",
    )

    # 10. 种子数据完整
    for table, expect in (("vehicle", 6), ("charging_pile", 4), ("system_config", 2)):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        n = cur.fetchone()[0]
        ck.check(f"种子数据 {table} = {expect} 行", n == expect, f"实际 {n}")

    cur.close()
    return ck


def main() -> int:
    ap = argparse.ArgumentParser(description="MySQL 8 真机验证（任务 5.6）")
    ap.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    ap.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    ap.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", ""))
    ap.add_argument("--db", default=os.getenv("MYSQL_DB", "bupt_charging_guard"))
    ap.add_argument("--json", default="", help="结果 JSON 输出路径（验收凭据）")
    args = ap.parse_args()

    driver, drv_name = load_driver()
    print(
        f"== MySQL 8 真机验证（驱动 {drv_name}，目标 {args.user}@{args.host}:{args.port}/{args.db}）=="
    )

    conn = driver.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.db,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        ck = run(conn)
    finally:
        conn.close()

    total, bad = len(ck.rows), len(ck.failed)
    print("=" * 60)
    print(f"结果：{total - bad}/{total} 通过" + ("" if not bad else f"，{bad} 项失败："))
    for r in ck.failed:
        print(f"  - {r['name']}  {r['detail']}")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(
                {"target": f"{args.host}:{args.port}/{args.db}", "rows": ck.rows},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"结果已写入：{args.json}")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
