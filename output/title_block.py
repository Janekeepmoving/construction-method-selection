# -*- coding: utf-8 -*-
"""页面框架模块 —— 在图纸上绘制简单的 736×574mm 外框。

坐标系原点在左下角 (0,0)，X 向右，Y 向上，单位 mm。
"""


class PageFrame:
    """简单页面外框。

    只绘制一个 736×574mm 的边界框（细线），
    内容区域在框内缩进 margin。
    """

    def __init__(self, settings: dict):
        ps = settings["paper_sizes"]["custom_736x574"]
        self.pw = ps["width"]
        self.ph = ps["height"]
        self.margin = ps.get("margin", 15)

    # ---------- 边界线 ----------

    def frame_lines(self):
        """返回外框的四条边线。"""
        return [
            ((0, 0), (self.pw, 0)),
            ((self.pw, 0), (self.pw, self.ph)),
            ((self.pw, self.ph), (0, self.ph)),
            ((0, self.ph), (0, 0)),
        ]

    # ---------- 内容区域 ----------

    @property
    def content_rect(self):
        """内容可用区域 (x, y, w, h)。"""
        m = self.margin
        return (m, m, self.pw - 2 * m, self.ph - 2 * m)

    @property
    def width(self):
        return self.pw

    @property
    def height(self):
        return self.ph
