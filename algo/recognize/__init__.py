"""CV 识别子包：车牌识别与车型判定（任务 2.4）。"""

from algo.recognize.plate import (
    is_valid_plate_text,
    judge_vtype_by_color,
    ocr_plate,
    recognize_frame,
)

__all__ = ["is_valid_plate_text", "judge_vtype_by_color", "ocr_plate", "recognize_frame"]
