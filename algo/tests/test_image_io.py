import pytest

np = pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")

from algo.recognize.image import read_image, write_image


def test_write_image_supports_windows_unicode_paths(tmp_path):
    path = tmp_path / "检测结果.png"
    pixels = np.full((12, 20, 3), [40, 80, 120], dtype=np.uint8)
    write_image(path, pixels)
    assert np.array_equal(read_image(path), pixels)


def test_read_image_supports_windows_unicode_paths(tmp_path):
    path = tmp_path / "中文目录" / "实拍.png"
    path.parent.mkdir()
    pixels = np.full((12, 20, 3), [40, 80, 120], dtype=np.uint8)
    success, encoded = cv2.imencode(".png", pixels)
    assert success
    encoded.tofile(path)
    assert np.array_equal(read_image(path), pixels)


def test_missing_or_invalid_image_returns_none(tmp_path):
    assert read_image(tmp_path / "missing.png") is None
    path = tmp_path / "invalid.jpg"
    path.write_bytes(b"not an image")
    assert read_image(path) is None
