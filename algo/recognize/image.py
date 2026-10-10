"""OpenCV image IO that supports Unicode paths on Windows."""

from pathlib import Path

import numpy as np


def read_image(path: str | Path) -> np.ndarray | None:
    import cv2

    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None


def write_image(path: str | Path, pixels: np.ndarray) -> None:
    import cv2

    success, encoded = cv2.imencode(Path(path).suffix, pixels)
    if not success:
        raise OSError(f"Could not encode image: {path}")
    encoded.tofile(path)
