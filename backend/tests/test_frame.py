"""Tests for GET /api/frame/latest and its snapshot-only contract."""

import os


def test_latest_frame_returns_newest_supported_image(client, tmp_path, monkeypatch):
    older = tmp_path / "older.jpg"
    newest = tmp_path / "newest.png"
    older.write_bytes(b"older-frame")
    newest.write_bytes(b"newest-frame")
    os.utime(older, (1_800_000_000, 1_800_000_000))
    os.utime(newest, (1_800_000_001, 1_800_000_001))
    monkeypatch.setenv("FRAME_SOURCE_DIR", str(tmp_path))

    response = client.get("/api/frame/latest")

    assert response.status_code == 200
    assert response.content == b"newest-frame"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("last-modified")
    assert response.headers["x-frame-ref"] == "newest.png"


def test_latest_frame_uses_mtime_then_name_for_ties(client, tmp_path, monkeypatch):
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    timestamp = 1_800_000_000
    os.utime(first, (timestamp, timestamp))
    os.utime(second, (timestamp, timestamp))
    monkeypatch.setenv("FRAME_SOURCE_DIR", str(tmp_path))

    response = client.get("/api/frame/latest")

    assert response.status_code == 200
    assert response.headers["x-frame-ref"] == "b.jpg"


def test_latest_frame_returns_404_when_no_supported_image(client, tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")
    monkeypatch.setenv("FRAME_SOURCE_DIR", str(tmp_path))

    response = client.get("/api/frame/latest")

    assert response.status_code == 404
