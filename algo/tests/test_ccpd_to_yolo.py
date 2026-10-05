"""CCPD 文件名解析的测试（任务 5.3）。

为什么单测的是**文件名解析**而不是转换全流程：CCPD 没有独立标注文件，
bbox 与车牌号全部编码在文件名里 —— 解析错了后面全错，而且错得很静默
（返回 None 就被 `continue` 跳过，最后报一句"没解析出任何样本"，
很容易误判成"下载的文件不对"）。第 2 周真踩了两次，故把格式变体钉死。

运行方式::

    .venv-algo\\Scripts\\python.exe -m pytest algo/tests -q
"""

from __future__ import annotations

from algo.tools import ccpd_to_yolo


# ---------------------------------------------------------------------------
# 两种分隔符：CCPD2020 用 &，CCPD2019 部分分发用 ,
# ---------------------------------------------------------------------------
def test_parse_ampersand_variant():
    """CCPD2020：``154&383_386&473``，7 位索引 → 蓝牌（燃油）。"""
    info = ccpd_to_yolo.parse_ccpd_name(
        "025-95_113-154&383_386&473-386&473_177&454_154&383_363&402-0_0_22_27_27_33_16-37-15.jpg"
    )
    assert info is not None
    assert info["bbox"] == [154, 383, 386, 473]
    assert len(info["plate"]) == 7
    assert info["vtype"] == "燃油"


def test_parse_comma_variant():
    """CCPD2019 子集：``302,471_372,497``，末尾还带 ``_ccpd_challenge_020298`` 后缀。"""
    info = ccpd_to_yolo.parse_ccpd_name(
        "0021-1_0-302,471_372,497-372,495_303,497_302,473_371,471"
        "-0_0_30_16_29_32_32-75-21_ccpd_challenge_020298.jpg"
    )
    assert info is not None
    assert info["bbox"] == [302, 471, 372, 497]
    assert info["vtype"] == "燃油"


def test_parse_green_plate_is_eight_chars():
    """8 位字符索引 → 绿牌（新能源），与文件名里的 ``_ccpd_green`` 后缀一致。"""
    info = ccpd_to_yolo.parse_ccpd_name(
        "0021479885057471265-90_262-315,502_393,527-393,527_318,526_315,502_393,502"
        "-0_0_3_29_30_31_32_33-185-10_ccpd_green_029398.jpg"
    )
    assert info is not None
    assert info["vtype"] == "新能源"
    assert len(info["plate"]) == 8


# ---------------------------------------------------------------------------
# 坏输入必须返回 None（被跳过），不能抛异常打断整批转换
# ---------------------------------------------------------------------------
def test_parse_rejects_malformed_names():
    for name in [
        "not-a-ccpd-file.jpg",  # 字段不够
        "025-95_113-abc&383_386&473-386&473_177&454-0_0_22_27_27_33_16-37-15.jpg",  # 坐标非数字
        "025-95_113-386&473_154&383-386&473_177&454-0_0_22_27_27_33_16-37-15.jpg",  # 右下在左上之前
    ]:
        assert ccpd_to_yolo.parse_ccpd_name(name) is None, name


def test_to_yolo_line_normalizes_to_center_format():
    """bbox → YOLO `0 cx cy w h`，且全部归一化到 0~1。"""
    line = ccpd_to_yolo._to_yolo_line([0, 0, 100, 50], 200, 100)
    cls, cx, cy, w, h = line.split(" ")
    assert cls == "0"
    assert (float(cx), float(cy), float(w), float(h)) == (0.25, 0.25, 0.5, 0.5)
