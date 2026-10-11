"""**加法迁移**：给已存在的库补上 v1.9 的新列（SQLite / MySQL 8 同口径）。

**为什么需要它**：`Base.metadata.create_all()` 只负责「建不存在的表」，
对**已存在的表**不会补列。本机开发库 `backend/app.db` 是 v1.8 时期建的，
加上列之后一跑就 `no such column: charging_pile.occupancy_id`；MySQL 8 演示库同理。
把「Git 回滚 ≠ 数据库回滚」写进文档容易，真让旧库能跑起来得有代码。

**只做加法**：新增列一律「可空」或「有默认值」，因此

- 旧代码在**带新列**的库上照常运行（向前兼容），可以先回滚代码再择机回退 DDL；
- 新代码在**带旧列**的库上，由本模块补齐后再运行。

手工执行的等价 SQL 见 `backend/sql/migration_v1.9.sql`（含回退段）。

维护人：汤瑾睿
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

#: v1.9 新增列：{表名: [(列名, MySQL DDL 片段, SQLite DDL 片段)]}
#: 两处 DDL 分开写是因为 SQLite 的 `ADD COLUMN` 不支持 `COMMENT`，
#: 且 `NOT NULL` 列必须带 DEFAULT（MySQL 也建议带，故都写上）。
NEW_COLUMNS: dict[str, list[tuple[str, str, str]]] = {
    "charging_pile": [
        ("occupancy_id", "VARCHAR(40) NULL", "VARCHAR(40)"),
        ("scenario", "VARCHAR(20) NULL", "VARCHAR(20)"),
    ],
    "occupation_record": [
        ("occupancy_id", "VARCHAR(40) NULL", "VARCHAR(40)"),
        ("notify_attempts", "TINYINT NOT NULL DEFAULT 0", "TINYINT NOT NULL DEFAULT 0"),
        ("notify_error", "VARCHAR(120) NULL", "VARCHAR(120)"),
    ],
}

#: 新增索引（SQLite / MySQL 语法一致，都是 `CREATE INDEX`）
NEW_INDEXES: dict[str, list[tuple[str, str]]] = {
    "charging_pile": [("idx_pile_occupancy", "occupancy_id")],
    "occupation_record": [("idx_occ_occupancy", "occupancy_id")],
}


def existing_columns(engine: Engine, table: str) -> set[str]:
    """读取表里已有的列名（MySQL 走 `information_schema`，SQLite 走 `PRAGMA`）。"""
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            return {row[1] for row in rows}

        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = :t"
            ),
            {"t": table},
        ).fetchall()
        return {row[0] for row in rows}


def _is_mysql(engine: Engine) -> bool:
    return engine.dialect.name != "sqlite"


def ensure_v19_columns(engine: Engine) -> list[str]:
    """补齐 v1.9 新增列与索引，返回实际执行的 DDL 列表（幂等：已存在则跳过）。

    幂等是刻意的：进程每次启动都会调用它，重复执行必须什么也不做。
    """
    applied: list[str] = []
    mysql = _is_mysql(engine)

    with engine.connect() as conn:
        for table, columns in NEW_COLUMNS.items():
            have = existing_columns(engine, table)
            for name, mysql_ddl, sqlite_ddl in columns:
                if name in have:
                    continue
                ddl = f"ALTER TABLE {table} ADD COLUMN {name} {mysql_ddl if mysql else sqlite_ddl}"
                conn.execute(text(ddl))
                applied.append(ddl)

        for table, indexes in NEW_INDEXES.items():
            for name, column in indexes:
                if mysql:
                    if _mysql_index_exists(conn, table, name):
                        continue
                    ddl = f"CREATE INDEX {name} ON {table} ({column})"
                else:
                    ddl = f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"
                conn.execute(text(ddl))
                applied.append(ddl)

        conn.commit()
    return applied


def _mysql_index_exists(conn, table: str, index: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = :t AND index_name = :i LIMIT 1"
        ),
        {"t": table, "i": index},
    ).fetchone()
    return row is not None
