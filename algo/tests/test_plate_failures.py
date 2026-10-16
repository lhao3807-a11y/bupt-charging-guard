"""第三周 real 读图与缺权重异常回归，不依赖已训练模型。"""

import pytest

pytest.importorskip("numpy")

from algo.recognize.plate import recognize_frame


def test_missing_image_is_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="图片不存在"):
        recognize_frame(str(tmp_path / "missing.jpg"))


def test_corrupt_image_is_decode_error(tmp_path):
    image = tmp_path / "corrupt.jpg"
    image.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="图片无法解码"):
        recognize_frame(str(image))


def test_missing_weights_is_visible(tmp_path):
    import cv2
    import numpy as np

    image = tmp_path / "valid.jpg"
    assert cv2.imwrite(str(image), np.zeros((32, 32, 3), dtype=np.uint8))
    with pytest.raises(FileNotFoundError):
        recognize_frame(str(image), weights=str(tmp_path / "missing.pt"))
