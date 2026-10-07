"""Latest captured image endpoint; this deliberately does not expose a video stream."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(tags=["frame"])

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_DIR = _BACKEND_DIR.parent
_DEFAULT_FRAME_DIR = _REPO_DIR / "algo" / "samples" / "frames"
_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.get("/api/frame/latest", summary="读取最新一帧截图")
def latest_frame() -> FileResponse:
    """Return the most recently modified image in ``FRAME_SOURCE_DIR``.

    A producer may refresh a file or place a new snapshot in the directory. This endpoint
    only returns one still image; it is not an MJPEG, WebSocket, or video stream.
    """
    source_dir = Path(os.environ.get("FRAME_SOURCE_DIR", str(_DEFAULT_FRAME_DIR)))
    try:
        candidates = [
            (
                entry.stat(follow_symlinks=False).st_mtime_ns,
                entry.name,
                entry.path,
            )
            for entry in os.scandir(source_dir)
            if entry.is_file(follow_symlinks=False)
            and Path(entry.name).suffix.lower() in _MEDIA_TYPES
        ]
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="当前没有可用截图，请检查帧采集目录。",
        ) from exc

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="当前没有可用截图，请将 JPEG、PNG 或 WebP 图片写入帧采集目录。",
        )

    _, filename, filepath = max(candidates, key=lambda item: (item[0], item[1]))
    return FileResponse(
        filepath,
        media_type=_MEDIA_TYPES[Path(filename).suffix.lower()],
        headers={"Cache-Control": "no-store", "X-Frame-Ref": filename},
    )
