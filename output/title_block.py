# -*- coding: utf-8 -*-
"""图框绘制模块 —— 在 DXF / PDF 图纸上绘制标准A2/A3图框。

图框基于用户提供的 DWG 模板结构，包含：
  - 外框（图幅边界，细实线）
  - 内框（绘图区域边界，粗实线，留装订边）
  - 标题栏（右下角，含项目信息栏）
  - 会签栏（左上角，预留）

所有坐标相对于图纸左下角 (0,0)，单位为 mm。
"""


class TitleBlock:
    """标准建筑图纸图框。

    支持 A2(594×420) 和 A3(420×297) 两种幅面，
    装订边在左侧，标题栏在右下角。
    """

    def __init__(self, title_block_config: dict, paper_size: str = "A2"):
        self._cfg = title_block_config
        self.size = paper_size
        ps = title_block_config[paper_size]
        self.pw = ps["paper_width"]    # 图幅宽
        self.ph = ps["paper_height"]   # 图幅高
        self.binding = ps["binding_margin"]  # 装订边宽度
        self.ml = ps["margin_left"]
        self.mr = ps["margin_right"]
        self.mt = ps["margin_top"]
        self.mb = ps["margin_bottom"]
        self.tb_cfg = ps["title_block"]      # 标题栏配置
        self.ts_cfg = ps.get("title_strip", {})  # 标题横条
        self.info_cfg = ps.get("info_area", {})   # 项目信息区域

    # ---------- 图框外框 ----------

    def outer_frame_lines(self):
        """外框：图幅边界细线。"""
        return [
            ((0, 0), (self.pw, 0)),
            ((self.pw, 0), (self.pw, self.ph)),
            ((self.pw, self.ph), (0, self.ph)),
            ((0, self.ph), (0, 0)),
        ]

    def inner_frame_lines(self):
        """内框：绘图区域边界粗线，留装订边在左侧。"""
        x0 = self.binding  # 左侧装订边
        y0 = self.mb
        x1 = self.pw - self.mr
        y1 = self.ph - self.mt
        return [
            ((x0, y0), (x1, y0)),
            ((x1, y0), (x1, y1)),
            ((x1, y1), (x0, y1)),
            ((x0, y1), (x0, y0)),
        ]

    @property
    def inner_rect(self):
        """绘图区域 (x, y, w, h)。"""
        return (
            self.binding,
            self.mb,
            self.pw - self.mr - self.binding,
            self.ph - self.mt - self.mb,
        )

    @property
    def width(self):
        return self.pw

    @property
    def height(self):
        return self.ph

    # ---------- 标题栏 ----------

    def title_block_rect(self):
        """返回标题栏外框。"""
        tb = self.tb_cfg
        x = tb["x_offset"]
        y = tb["y_offset"]
        w = tb["width"]
        h = tb["height"]
        return (x, y, w, h)

    def title_block_lines(self):
        """标题栏所有横竖线。"""
        lines = []
        tb = self.tb_cfg
        x0, y0 = tb["x_offset"], tb["y_offset"]
        w, h = tb["width"], tb["height"]

        # 外框
        lines.append(((x0, y0), (x0 + w, y0)))
        lines.append(((x0 + w, y0), (x0 + w, y0 + h)))
        lines.append(((x0 + w, y0 + h), (x0, y0 + h)))
        lines.append(((x0, y0 + h), (x0, y0)))

        # 内部分隔线
        cy = y0
        for row in tb.get("rows", []):
            cy += row["height"]
            lines.append(((x0, cy), (x0 + w, cy)))
            col_x = x0
            for col in row.get("cols", []):
                col_x += col["width"]
                lines.append(((col_x, cy - row["height"]), (col_x, cy)))

        return lines

    def title_block_texts(self):
        """标题栏内所有固定文本与占位。"""
        texts = []
        tb = self.tb_cfg
        x0, y0 = tb["x_offset"], tb["y_offset"]
        cy = y0
        for row in tb.get("rows", []):
            cx = x0
            for col in row.get("cols", []):
                texts.append({
                    "text": col["label"],
                    "x": cx + col["width"] / 2,
                    "y": cy + row["height"] / 2,
                    "width": col["width"],
                    "height": row["height"],
                    "align": "center",
                })
                cx += col["width"]
            cy += row["height"]
        return texts

    # ---------- 标题横条（图名区域） ----------

    def title_strip_rect(self):
        ts = self.ts_cfg
        return (ts.get("x_offset", 0), ts.get("y_offset", 0),
                ts.get("width", 0), ts.get("height", 0))

    # ---------- 项目信息区域 ----------

    def info_area_lines(self):
        """项目信息区域外框。"""
        info = self.info_cfg
        x = info["x"]
        y = info["y_top"] - info["height"]
        w = info["width"]
        h = info["height"]
        return [
            ((x, y), (x + w, y)),
            ((x + w, y), (x + w, y + h)),
            ((x + w, y + h), (x, y + h)),
            ((x, y + h), (x, y)),
        ]

    def info_area_fields(self):
        """项目信息区域中各字段位置。"""
        return self.info_cfg.get("fields", [])
