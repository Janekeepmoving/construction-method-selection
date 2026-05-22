# -*- coding: utf-8 -*-
"""PDF 图纸输出模块 —— 使用 reportlab 将表格与图框叠加输出为矢量 PDF。"""

import os
from reportlab.lib.pagesizes import A2, A3
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle

from .title_block import TitleBlock

# 尝试注册中文字体
_FONT_REGISTERED = False


def _try_register_font():
    """尝试注册仿宋字体。"""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    # 常见的仿宋字体路径
    candidates = [
        ("C:/Windows/Fonts/simfang.ttf", "FangSong"),
        ("C:/Windows/Fonts/STFANGSO.TTF", "FangSong"),
        ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
        ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_REGISTERED = True
                return name
            except Exception:
                continue
    return "Helvetica"


class PDFExporter:
    """将表格数据与图框叠加输出为 PDF 文件。"""

    def __init__(self, settings: dict, title_block_config: dict):
        self._settings = settings
        self._tb_config = title_block_config
        self._font_size_body = settings["fonts"]["body"]["size"]
        self._font_size_header = settings["fonts"]["header"]["size"]
        self._font_size_title = settings["fonts"]["title"]["size"]
        self._font_name = None  # 延迟注册

    def export(self, table_data: dict, project_info, paper_size: str,
               output_path: str) -> str:
        """导出表格到 PDF 文件。"""
        self._font_name = _try_register_font()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        tb = TitleBlock(self._tb_config, paper_size)
        page_size = A2 if paper_size == "A2" else A3

        c = canvas.Canvas(output_path, pagesize=page_size)
        pw, ph = page_size

        # 绘制图框
        self._draw_title_block_on_canvas(c, tb, project_info, pw, ph)

        # 计算表格可用区域
        usable = tb.inner_rect
        ux, uy, uw, uh = usable
        margin = 10 * mm
        table_x = ux + margin
        table_y = uy + margin
        table_w = uw - 2 * margin
        max_table_h = uh - 2 * margin

        self._draw_table_pdf(c, table_data, table_x, table_y,
                              table_w, max_table_h, ph)

        c.save()
        return output_path

    def _draw_title_block_on_canvas(self, c, tb: TitleBlock, proj_info,
                                     pw: float, ph: float):
        """在 PDF 画布上绘制图框。"""
        # 外框细线
        c.setLineWidth(0.13)
        c.setStrokeColor(colors.black)
        for (x1, y1), (x2, y2) in tb.outer_frame_lines():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

        # 内框粗线
        c.setLineWidth(0.4)
        for (x1, y1), (x2, y2) in tb.inner_frame_lines():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

        # 标题栏
        c.setLineWidth(0.25)
        for (x1, y1), (x2, y2) in tb.title_block_lines():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

        # 信息区域
        c.setLineWidth(0.4)
        for (x1, y1), (x2, y2) in tb.info_area_lines():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

        # 项目信息文字
        info = tb.info_cfg
        field_map = {
            "项目名称": proj_info.project_name,
            "图纸名称": proj_info.drawing_name,
            "图号": proj_info.drawing_number,
        }
        for field in info.get("fields", []):
            label = field["label"]
            val = field.get("value", field_map.get(label, ""))
            fx = (field["x"] + 2) * mm
            fy = (info["y_top"] - info["height"] / 2) * mm
            display = f"{label}: {val}" if val else label
            c.setFont(self._font_name, 3.5 * mm)
            c.drawString(fx, fy, display)

        # 标题栏内文字
        for tinfo in tb.title_block_texts():
            c.setFont(self._font_name, 2.5 * mm)
            tx = tinfo["x"] * mm
            ty = tinfo["y"] * mm
            c.drawString(tx, ty, tinfo["text"])

    def _draw_table_pdf(self, c, table_data: dict, tx: float, ty: float,
                         tw: float, max_h: float, ph: float):
        """在 PDF 画布上绘制表格（简单逐行绘制）。"""
        cols = table_data["columns"]
        col_ratios = [c["width"] for c in cols]
        ratio_sum = sum(col_ratios)
        col_widths = [r / ratio_sum * tw for r in col_ratios]

        th = table_data["title_height"] * mm
        hh = table_data["header_height"] * mm
        rh = table_data["row_height"] * mm

        cur_y_mm = ty + max_h

        # 标题行
        c.setFont(self._font_name, self._font_size_title * mm)
        title = table_data["title"]
        c.drawString(tx + tw / 2 - len(title) * 2 * mm, cur_y_mm - th * 0.7, title)
        cur_y_mm -= th

        # 表头
        c.setFont(self._font_name, self._font_size_header * mm)
        for ci, col in enumerate(cols):
            cx = tx + sum(col_widths[:ci])
            c.drawString(cx + 1 * mm, cur_y_mm - hh * 0.6, col["header"])
        cur_y_mm -= hh

        # 数据行
        c.setFont(self._font_name, self._font_size_body * mm)
        for row in table_data["rows"]:
            if cur_y_mm - rh < ty:
                break  # 超出页面
            cells = row.get("cells", [])
            colspan = row.get("colspan", 1)
            if colspan > 1 and cells:
                c.drawString(tx + 1 * mm, cur_y_mm - rh * 0.6, str(cells[0]))
            else:
                for ci, cell_text in enumerate(cells):
                    if ci >= len(col_widths):
                        break
                    cx = tx + sum(col_widths[:ci])
                    c.drawString(cx + 1 * mm, cur_y_mm - rh * 0.6, str(cell_text))
            cur_y_mm -= rh
