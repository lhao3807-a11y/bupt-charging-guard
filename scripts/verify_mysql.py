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

**第 3 周扩展（T7）**：旧基线 19 项只验到 v1.8 的 schema。v1.9 新增了占用标识与
提醒结果字段（契约 §3.6 / §6.3），本脚本补验第 11–16 组：新列存在且类型正确、
``notify_attempts`` 有默认值且非空、新索引建起来了、含中文失败原因的记录能原样读回、
``occupancy_id`` 为 NULL 的历史行不与新数据匹配（``<=>`` 空值安全比较），
以及 ``app/migrate.py`` 的**加法迁移在真机上是幂等的**（先删列再补回、补两次）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
BACKEND_DIR = os.path.join(REPO, "backend")
SCHEMA_SQL = os.path.join(BACKEND_DIR, "sql", "schema.sql")

#: 期望的四张表与存储引擎（契约 §3）
EXPECTED_TABLES = ("vehicle", "charging_pile", "occupation_record", "system_config")

#: v1.9 新增列（契约 §3.6 / §6.3）与期望的 MySQL 类型前缀
NEW_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "charging_pile": [("occupancy_id", "varchar(40)"), ("scenario", "varchar(20)")],
    "occupation_record": [
        ("occupancy_id", "varchar(40)"),
        ("notify_attempts", "tinyint"),
        ("notify_error", "varchar(120)"),
    ],
}

#: v1.9 新增索引
NEW_INDEXES: dict[str, tuple[str, ...]] = {
    "charging_pile": ("idx_pile_occupancy",),
    "occupation_record": ("idx_occ_occupancy",),
}


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


def run(conn, *, driver_name: str = "pymysql", args=None) -> Checker:
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

    _check_v19_columns(cur, ck)
    _check_v19_write_read(cur, ck, conn)
    _check_migration_idempotent(ck, driver_name, args)

    cur.close()
    return ck


# ---------------------------------------------------------------------------
# 第 3 周 T7：v1.9 新列 / 默认值 / 索引 / 空值语义 / 加法迁移幂等
# ---------------------------------------------------------------------------
def _columns(cur, table: str) -> dict[str, tuple[str, str, str]]:
    """列名 → (类型, 是否可空, 默认值)。"""
    cur.execute(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        (table,),
    )
    return {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}


def _check_v19_columns(cur, ck) -> None:
    """新列存在且类型正确；`notify_attempts` 必须 NOT NULL 且有默认值。"""
    for table, cols in NEW_COLUMNS.items():
        have = _columns(cur, table)
        for name, type_prefix in cols:
            info = have.get(name)
            ck.check(
                f"{table}.{name} 存在且类型为 {type_prefix}",
                bool(info) and info[0].lower().startswith(type_prefix),
                str(info) if info else "列不存在",
            )

    occ = _columns(cur, "occupation_record")
    attempts = occ.get("notify_attempts")
    ck.check(
        "occupation_record.notify_attempts 是 NOT NULL 且默认 0",
        bool(attempts) and attempts[1] == "NO" and str(attempts[2]) == "0",
        str(attempts),
    )

    cur.execute(
        "SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"
    )
    indexes = {r[0] for r in cur.fetchall()}
    for table, names in NEW_INDEXES.items():
        for name in names:
            ck.check(f"索引 {name} 已建立（{table}）", name in indexes, f"现有 {sorted(indexes)}")


def _check_v19_write_read(cur, ck, conn) -> None:
    """写入带占用标识与失败原因的记录并原样读回（中文不能乱码/截断）。"""
    reason = "车主未绑定手机号"
    cur.execute(
        "INSERT INTO occupation_record "
        "(plate, vtype, pile_id, occupancy_id, rule_hit, occur_time, "
        " notify_status, notify_attempts, notify_error) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "京TEST02",
            "新能源",
            "PILE-TEST2",
            "PILE-TEST2@20260908100000000000",
            2,
            "2026-09-08 10:00:00",
            "失败",
            2,
            reason,
        ),
    )
    # 另一行故意留空占用标识，代表「历史数据」
    cur.execute(
        "INSERT INTO occupation_record "
        "(plate, vtype, pile_id, rule_hit, occur_time, notify_status) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        ("京TEST03", "燃油", "PILE-TEST2", 1, "2026-09-08 09:00:00", "未提醒"),
    )
    conn.commit()

    cur.execute(
        "SELECT occupancy_id, notify_attempts, notify_error FROM occupation_record "
        "WHERE plate = %s",
        ("京TEST02",),
    )
    row = cur.fetchone()
    ck.check(
        "占用标识与失败原因原样读回（中文不乱码）",
        row == ("PILE-TEST2@20260908100000000000", 2, reason),
        f"读出 {row!r}",
    )

    # 空值安全比较：判重键里 occupancy_id 为 NULL 的行只与 NULL 行匹配
    cur.execute(
        "SELECT COUNT(*) FROM occupation_record WHERE pile_id = %s AND occupancy_id <=> NULL",
        ("PILE-TEST2",),
    )
    null_rows = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM occupation_record WHERE pile_id = %s AND occupancy_id = %s",
        ("PILE-TEST2", "PILE-TEST2@20260908100000000000"),
    )
    matched = cur.fetchone()[0]
    ck.check(
        "NULL 占用标识不与新数据匹配（判重键空值安全）",
        null_rows == 1 and matched == 1,
        f"NULL 行 {null_rows}、匹配新标识 {matched}",
    )

    cur.execute("DELETE FROM occupation_record WHERE plate IN (%s, %s)", ("京TEST02", "京TEST03"))
    conn.commit()


def _sqlalchemy_url(driver_name: str, args) -> str:
    """把驱动名与连接参数拼成 SQLAlchemy URL（真机跑 `app/migrate.py` 需要）。"""
    from urllib.parse import quote_plus

    dialect = {
        "pymysql": "mysql+pymysql",
        "mysql-connector-python": "mysql+mysqlconnector",
        "mysqlclient": "mysql+mysqldb",
    }[driver_name]
    secret = quote_plus(args.password or "")
    auth = f"{args.user}:{secret}@" if secret else f"{args.user}@"
    return f"{dialect}://{auth}{args.host}:{args.port}/{args.db}?charset=utf8mb4"


def _check_migration_idempotent(ck, driver_name: str, args) -> None:
    """**真机验证 `app/migrate.py`**：先把新列删掉（模拟 v1.8 老库），再让迁移补回来。

    只验「列存在」不够 —— 真正会翻车的是「老库升级」这条路径，而 SQLite 单测
    覆盖不到 MySQL 的 `ALTER TABLE ... ADD COLUMN` 与索引语法差异。
    """
    if args is None:  # 被其他调用方直接用时跳过（不伪造一次假验证）
        return
    try:
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        from app import migrate
        from sqlalchemy import create_engine, text
    except ImportError as exc:  # pragma: no cover - 环境问题
        ck.check("app/migrate.py 可导入（需要 sqlalchemy）", False, f"{type(exc).__name__}: {exc}")
        return

    engine = create_engine(_sqlalchemy_url(driver_name, args), future=True)
    drop = [
        (
            "ALTER TABLE charging_pile DROP INDEX idx_pile_occupancy, DROP COLUMN occupancy_id, "
            "DROP COLUMN scenario"
        ),
        (
            "ALTER TABLE occupation_record DROP INDEX idx_occ_occupancy, DROP COLUMN occupancy_id, "
            "DROP COLUMN notify_attempts, DROP COLUMN notify_error"
        ),
    ]
    with engine.connect() as conn:
        for stmt in drop:
            conn.execute(text(stmt))
        conn.commit()

    applied = migrate.ensure_v19_columns(engine)
    ck.check(
        "加法迁移把 5 个新列与 2 个索引补回（v1.8 老库升级）",
        len(applied) == 7,
        f"补了 {len(applied)} 条：{applied}",
    )

    again = migrate.ensure_v19_columns(engine)
    ck.check("加法迁移幂等（第二次执行无操作）", again == [], f"第二次又执行了 {again}")
    engine.dispose()


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
        ck = run(conn, driver_name=drv_name, args=args)
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
