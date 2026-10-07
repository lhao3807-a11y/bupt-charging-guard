# 网络车辆与充电场景补充素材

本目录补充 80 张公开授权的车辆、道路停车和电动汽车充电照片，供算法数据筛选与人工标注使用。图像位于 `images/`，逐图来源、作者、许可、尺寸和 SHA-256 摘要见 [`licenses.csv`](licenses.csv)。

## 当前状态

- 共 80 张，来自 Flickr（73 张）和 Wikimedia Commons（7 张）。
- 许可分布：CC BY 57 张、CC BY-SA 22 张、CC0 1 张。各文件的具体许可和署名要求以清单对应行及来源页为准。
- 图片覆盖道路交通、停车和充电设备/车辆等一般场景，含部分中国城市及低速电动车素材；它们不是校园实拍样本。
- 图片尚未完成人工框标注，也未进入 `data.yaml`、训练/验证划分或模型训练。使用前须按项目任务补充车辆/车牌框和适用场景标签；不能从静态普通车图推断“燃油占位、新能源充电中、新能源空闲久停、已充满”状态。
- 因此本目录只表示公开素材补充完成，不代表 PLAN §2.2 / §5.3 的四类校园场景验收完成。校园实拍、四类各不少于 30 张及标注仍需单独完成。

## 署名与复用

复用单张图像时，按 `licenses.csv` 提供的作者、来源页和许可链接保留署名，并遵守对应许可的再分发要求。Openverse 的记录用于发现素材；最终许可信息应以每张图像的原始来源页为准。

- [Openverse API](https://api.openverse.org/v1/)
- [Wikimedia Commons：在 Wikimedia 之外复用内容](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/en)
