"""CV 识别子包：车牌识别与车型判定（任务 2.4）。"""

__all__ = [
    "crop_plate_roi",
    "is_valid_plate_text",
    "judge_vtype_by_color",
    "ocr_plate",
    "ocr_plate_in_frame",
    "recognize_frame",
]


def __getattr__(name):
    """Keep geometry and reporting usable without optional CV dependencies."""
    if name in __all__:
        from importlib import import_module

        return getattr(import_module("algo.recognize.plate"), name)
    raise AttributeError(name)
