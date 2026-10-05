"""系统参数读写的测试（契约 v1.6 §6.9，第 5 页 / PLAN 任务 5.7 的 C3）。

守 §7 红线是本组测试的全部意义：

- **白名单只有两个键**：未知 key → 422（野键进了 `system_config` 会直接改业务判定）
- **取值范围 1–1440 分钟**：0 会让规则②③对任何车立刻命中
- **值以字符串落库**，与 `system_config.value` 的 VARCHAR 类型一致
- **改完立刻影响规则引擎**（专门一条端到端用例，证明配置不是"改着好玩"的）
- 缺失抛 `ConfigMissingError`，**不静默兜底**
"""

from __future__ import annotations

from datetime import datetime

import pytest
from app import models as m
from app.rule_engine import ConfigMissingError, get_config_int, judge
from app.schemas import ConfigUpdate, RecognitionResult

CONFIG_FIELDS = {"key", "value", "note"}
WHITELIST = ("full_timeout_min", "abnormal_park_min")


def _get(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _put(client, payload: dict):
    return client.put("/api/config", json=payload)


def _current_int(client, key: str) -> int:
    """读回某项配置的当前整型值（用于「422 后没被改坏」这类断言）。"""
    values = {item["key"]: item["value"] for item in _get(client)["items"]}
    return int(values[key])


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------
def test_get_returns_two_whitelisted_items(client):
    body = _get(client)
    assert body["total"] == 2
    assert [item["key"] for item in body["items"]] == list(WHITELIST)
    assert set(body["items"][0]) == CONFIG_FIELDS


def test_get_value_is_string(client):
    """`value` 是字符串（库里 VARCHAR），不是数字 —— 避免类型漂移。"""
    values = {item["key"]: item["value"] for item in _get(client)["items"]}
    assert values == {"full_timeout_min": "30", "abnormal_park_min": "30"}


def test_get_has_note(client):
    assert all(item["note"] for item in _get(client)["items"])


# ---------------------------------------------------------------------------
# PUT /api/config
# ---------------------------------------------------------------------------
def test_put_updates_value_and_returns_full_config(client):
    resp = _put(client, {"full_timeout_min": 45})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2  # 返回全量，前端不必再发一次 GET
    values = {item["key"]: item["value"] for item in body["items"]}
    assert values["full_timeout_min"] == "45"
    assert values["abnormal_park_min"] == "30"  # 未提交的那项保持原值


def test_put_persists_and_is_visible_to_next_get(client):
    assert _put(client, {"abnormal_park_min": 60}).status_code == 200
    values = {item["key"]: item["value"] for item in _get(client)["items"]}
    assert values["abnormal_park_min"] == "60"


def test_put_can_update_both_at_once(client):
    values = {
        item["key"]: item["value"]
        for item in _put(client, {"full_timeout_min": 90, "abnormal_park_min": 15}).json()["items"]
    }
    assert values == {"full_timeout_min": "90", "abnormal_park_min": "15"}


def test_put_stores_string_in_db(db_session, client):
    """落库是字符串：换库（MySQL）时不会出现「存进去 45 读出来 '45'」的分歧。"""
    assert _put(client, {"full_timeout_min": 45}).status_code == 200
    row = db_session.get(m.SystemConfig, "full_timeout_min")
    assert row.value == "45" and isinstance(row.value, str)


def test_put_unknown_key_is_422(client):
    """红线：野键不得写进 system_config。"""
    resp = _put(client, {"full_timeout_min": 45, "sms_enabled": "1"})
    assert resp.status_code == 422, resp.text
    # 未知键被拒时，合法键也不应被写入（整请求拒绝）
    assert _current_int(client, "full_timeout_min") == 30


@pytest.mark.parametrize("bad", [{"sms_api_key": "x"}, {"full_timeout": 30}, {"": 1}])
def test_put_rejects_any_non_whitelisted_key(client, bad):
    assert _put(client, bad).status_code == 422


@pytest.mark.parametrize("bad_value", [0, -1, 1441, 100000])
def test_put_rejects_out_of_range(client, bad_value):
    """0 → 规则②③对所有车立刻命中；1441 分钟 > 24 小时，无意义。"""
    assert _put(client, {"full_timeout_min": bad_value}).status_code == 422


@pytest.mark.parametrize("good_value", [1, 30, 1440])
def test_put_accepts_boundary_values(client, good_value):
    assert _put(client, {"full_timeout_min": good_value}).status_code == 200
    assert _current_int(client, "full_timeout_min") == good_value


def test_put_empty_body_is_422(client):
    assert _put(client, {}).status_code == 422


def test_put_null_only_body_is_422(client):
    """两个键都显式给 null → 等同空请求。"""
    assert _put(client, {"full_timeout_min": None}).status_code == 422


def test_update_schema_only_has_two_keys():
    """类型层面收口白名单（与路由白名单双重保险）。"""
    assert set(ConfigUpdate.model_fields) == set(WHITELIST)
    assert ConfigUpdate.model_config["extra"] == "forbid"


# ---------------------------------------------------------------------------
# 与规则引擎联动 / 缺失不兜底
# ---------------------------------------------------------------------------
def test_config_change_affects_rule_engine(client, db_session):
    """端到端：把 full_timeout_min 从 30 放宽到 120，同一辆车就不再命中规则③。

    种子桩 PILE-002：已充满，end_time = 09-08 09:20，绑定新能源车 京AD67890。
    """
    moment = datetime(2026, 9, 8, 10, 0)  # 充满后 40 分钟
    recognition = RecognitionResult(
        plate="京AD67890",
        vtype="新能源",
        confidence=0.9,
        bbox=[0, 0, 1, 1],
        frame_time=moment,
    )

    assert judge(recognition, db_session).rule_hit == m.RULE_FULL_NOT_MOVED  # 40 > 30

    assert _put(client, {"full_timeout_min": 120}).status_code == 200
    assert judge(recognition, db_session) is None  # 40 < 120 → 正常


def test_get_config_int_reads_updated_value(client, db_session):
    assert _put(client, {"abnormal_park_min": 75}).status_code == 200
    assert get_config_int(db_session, "abnormal_park_min") == 75


def test_missing_key_raises_instead_of_defaulting(db_session):
    """阈值缺失是数据故障：必须炸出来，而不是拿默认值蒙混（契约 §7）。"""
    db_session.delete(db_session.get(m.SystemConfig, "full_timeout_min"))
    db_session.commit()
    with pytest.raises(ConfigMissingError):
        get_config_int(db_session, "full_timeout_min")
