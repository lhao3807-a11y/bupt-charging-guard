"""MySQL 8 真机验证脚本的**纯逻辑**测试（任务 5.6）。

`scripts/verify_mysql.py` 真正跑起来需要一台 MySQL 8（本机没有，见
`docs/WEEK2_PROGRESS_TANG.md` §5.6）。但脚本里**不依赖数据库的部分**必须现在就测：

- `split_statements`：建表 SQL 切分错了，整套验证会静默少建表、
  然后一堆断言莫名 FAIL，排查方向完全跑偏
- `Checker`：一处断言抛异常不该吃掉后面所有结果

这两块坏了，等真机到了才发现就白跑一趟。

运行方式（后端环境即可，无需 MySQL）::

    .venv\\Scripts\\python.exe -m pytest backend/tests -q
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))

import verify_mysql

SCHEMA = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql"))


def test_split_statements_drops_comments_and_blanks():
    sql = """
    -- 这是注释，含 ; 也不该被当分隔符
    CREATE TABLE t (a INT);   -- 行尾注释
    INSERT INTO t VALUES (1);
    """
    stmts = verify_mysql.split_statements(sql)
    assert stmts == ["CREATE TABLE t (a INT)", "INSERT INTO t VALUES (1)"]


def test_split_statements_on_real_schema():
    """对**真实**的 schema.sql 切分：语句数合理，且不含注释残留。"""
    with open(SCHEMA, encoding="utf-8") as fh:
        stmts = verify_mysql.split_statements(fh.read())
    assert len(stmts) > 10, stmts
    for s in stmts:
        assert not s.startswith("--"), s
        assert "\n--" not in s, s
    # 必须有四张建表语句 + 三段种子 INSERT
    assert sum(1 for s in stmts if s.upper().startswith("CREATE TABLE")) == 4
    assert sum(1 for s in stmts if s.upper().startswith("INSERT INTO")) == 3


def test_split_statements_keeps_semicolon_free_strings_intact():
    """种子数据里的中文/引号不能被切坏。"""
    with open(SCHEMA, encoding="utf-8") as fh:
        stmts = verify_mysql.split_statements(fh.read())
    seeds = [s for s in stmts if s.upper().startswith("INSERT INTO SYSTEM_CONFIG")]
    assert len(seeds) == 1, [s[:60] for s in stmts]
    assert "full_timeout_min" in seeds[0] and "abnormal_park_min" in seeds[0]


def test_checker_collects_both_pass_and_fail():
    ck = verify_mysql.Checker()
    ck.check("会通过的一项", True)
    ck.check("会失败的一项", False, "原因")
    assert len(ck.rows) == 2
    assert [r["name"] for r in ck.failed] == ["会失败的一项"]
    assert ck.failed[0]["detail"] == "原因"


def test_checker_keeps_going_after_failure():
    """一处 FAIL 不能中断后续检查 —— 否则一次只能看到一个失败项。"""
    ck = verify_mysql.Checker()
    ck.check("第一项", False)
    ck.check("第二项", True)
    ck.check("第三项", False)
    assert len(ck.rows) == 3
    assert len(ck.failed) == 2


def test_expected_tables_matches_schema():
    """脚本里写死的四张表必须和 schema.sql 一致，改了表要两边同步。"""
    with open(SCHEMA, encoding="utf-8") as fh:
        stmts = verify_mysql.split_statements(fh.read())
    declared = {
        s.upper().split("CREATE TABLE ")[1].split("(")[0].strip().lower()
        for s in stmts
        if s.upper().startswith("CREATE TABLE")
    }
    assert declared == set(verify_mysql.EXPECTED_TABLES), declared
