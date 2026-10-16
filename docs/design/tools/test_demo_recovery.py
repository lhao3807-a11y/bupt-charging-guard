import json

import httpx
import pytest

from docs.design.tools import demo_recovery_shots as recovery


def test_recovery_binds_phone_and_verifies_idempotence():
    calls = []
    count = 0

    def handle(request):
        nonlocal count
        body = json.loads(request.content)
        calls.append((request.method, request.url.path, body))
        if request.method == "PUT":
            return httpx.Response(200, json={"phone": body["phone"]})
        if body["retry"] is False:
            return httpx.Response(
                200,
                json={
                    "id": 3,
                    "notify_status": "失败",
                    "notify_attempts": 0,
                    "reason": "车主未绑定手机号",
                },
            )
        count += 1
        return httpx.Response(
            200,
            json={
                "id": 3,
                "notify_status": "已提醒",
                "notify_attempts": 1,
                "already_sent": count > 1,
                "exhausted": False,
                "conflict": False,
            },
        )

    phases = []
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = recovery.recover_record(
            client,
            "http://demo",
            {"id": 3, "plate": "京A88888", "vtype": "燃油"},
            "13800138000",
            phases.append,
        )
    assert phases == ["w601-1-failed", "w601-2-recovered", "w601-3-final"]
    assert calls[1][0] == "PUT"
    assert calls[2][2] == {"id": 3, "retry": True}
    assert result["final"]["already_sent"] is True


def test_legacy_notify_response_is_rejected():
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"notify_status": "失败"}))
    ) as client, pytest.raises(ValueError, match="v1.9"):
        recovery.recover_record(
            client,
            "http://demo",
            {"id": 3, "plate": "京A88888", "vtype": "燃油"},
            "13800138000",
            lambda _: None,
        )


def test_failed_retry_does_not_produce_success_screenshot():
    phases = []

    def handle(request):
        if request.method == "PUT":
            return httpx.Response(200, json={})
        retry = json.loads(request.content)["retry"]
        return httpx.Response(
            200,
            json={
                "id": 3,
                "notify_status": "失败",
                "notify_attempts": int(retry),
                "reason": "车主未绑定手机号",
            },
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handle)) as client,
        pytest.raises(ValueError, match="重试未成功"),
    ):
        recovery.recover_record(
            client, "http://demo", {"id": 3, "plate": "京A88888", "vtype": "燃油"},
            "13800138000", phases.append,
        )
    assert phases == ["w601-1-failed"]
