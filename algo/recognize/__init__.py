"""CV 识别子包：车牌识别与车型判定（任务 2.4）。"""

from algo.recognize.plate import (
    crop_plate_roi,
    is_valid_plate_text,
    judge_vtype_by_color,
    ocr_plate,
    ocr_plate_in_frame,
    recognize_frame,
)

__all__ = [
    "crop_plate_roi",
    "is_valid_plate_text",
    "judge_vtype_by_color",
    "ocr_plate",
    "ocr_plate_in_frame",
    "recognize_frame",
]
