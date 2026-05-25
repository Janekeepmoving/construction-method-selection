# -*- coding: utf-8 -*-
"""PDF 图纸输出模块 —— 流式 5 栏布局，按做法类型顺序从上到下、从左到右排版。"""

import os
from reportlab.lib.pagesizes import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .title_block import PageFrame

_FONT_REGISTERED = False


def _try_register_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
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
    """流式 5 栏布局 PDF 输出。"""

    def __init__(self, settings: dict, table_styles: dict):
        self._settings = settings
        self._styles = table_styles
        self._font_size_body = settings["fonts"]["body"]["size"]
        self._font_size_header = settings["fonts"]["header"]["size"]
        self._font_size_title = settings["fonts"]["title"]["size"]
        self._font_name = None
        self._pads = table_styles.get("cell_padding",
                                       {"horizontal": 1.0, "vertical": 0.5})

    def export(self, table_data: dict, project_info,
               output_path: str) -> str:
        self._font_name = _try_register_font()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        pf = PageFrame(self._settings)
        pw_mm = pf.pw * mm
        ph_mm = pf.ph * mm

        pages = self._paginate_flow(table_data, pf)
        base, ext = os.path.splitext(output_path)

        for page_idx, page_cols in enumerate(pages):
            page_path = output_path if len(pages) == 1 else \
                f"{base}_p{page_idx + 1}{ext}"

            c = canvas.Canvas(page_path, pagesize=(pw_mm, ph_mm))
            self._draw_frame(c, pf)
            self._draw_page(c, page_cols, table_data["sub_columns"],
                            pf, page_idx + 1, len(pages))
            c.save()

        return output_path if len(pages) == 1 else output_path

    def _draw_frame(self, c, pf: PageFrame):
        c.setLineWidth(0.13)
        c.setStrokeColor(colors.black)
        for (x1, y1), (x2, y2) in pf.frame_lines():
            c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)

    # ---------- 流式分页 ----------

    def _paginate_flow(self, table_data: dict, pf: PageFrame) -> list:
        """流式布局：与 DXF 导出相同的分页逻辑。"""
        sections = table_data.get("sections", [])
        section_h = self._styles.get("section_header_height", 7)
        row_h = self._styles.get("row_height", 6.5)
        method_hdr_h = self._styles.get("method_header_height", 7)

        blocks = []
        for sec in sections:
            blocks.append({"type": "section_header",
                           "title": sec["section_title"],
                           "height": section_h})
            for m in sec.get("methods", []):
                n_layers = len(m.get("layers", [])) or 1
                mh = method_hdr_h + n_layers * row_h
                blocks.append({"type": "method",
                               "data": m,
                               "height": mh})

        if not blocks:
            return [[[] for _ in range(5)]]

        title_h = self._styles.get("title_height", 12)
        sub_h = self._styles.get("header_height", 8)
        _, _, _, content_h = pf.content_rect
        col_avail_h = content_h - title_h - sub_h

        pages = []
        block_idx = 0
        total = len(blocks)

        while block_idx < total:
            page_cols = [[] for _ in range(5)]
            col_cursors = [col_avail_h] * 5

            for ci in range(5):
                while block_idx < total and col_cursors[ci] > 0:
                    block = blocks[block_idx]
                    if col_cursors[ci] >= block["height"]:
                        if block["type"] == "section_header" and page_cols[ci]:
                            need = block["height"]
                            look = block_idx + 1
                            while look < total and blocks[look]["type"] == "section_header":
                                need += blocks[look]["height"]
                                look += 1
                            if look < total and blocks[look]["type"] == "method":
                                need += blocks[look]["height"]
                            if col_cursors[ci] < need:
                                break
                        page_cols[ci].append(block)
                        col_cursors[ci] -= block["height"]
                        block_idx += 1
                    else:
                        if not page_cols[ci]:
                            page_cols[ci].append(block)
                            col_cursors[ci] -= block["height"]
                            block_idx += 1
                        break

            pages.append(page_cols)

        return pages

    # ---------- 页面绘制 ----------

    def _draw_page(self, c, page_cols: list, sub_columns: list,
                   pf: PageFrame, page_num: int, total_pages: int):
        cx, cy, cw, ch = pf.content_rect
        n_cols = 5
        gap = self._styles.get("column_gap", 2)
        col_w = (cw - (n_cols - 1) * gap) / n_cols

        title_h = self._styles.get("title_height", 12)

        title_text = f"{self._styles['table_type']['name']}（第{page_num}页/共{total_pages}页）" \
            if total_pages > 1 else self._styles["table_type"]["name"]
        c.setFont(self._font_name, self._font_size_title * mm)
        c.drawString((cx + cw / 2 - len(title_text) * 2) * mm,
                     (cy + ch - title_h * 0.3) * mm, title_text)

        col_top = cy + ch - title_h
        col_bottom = cy
        section_h = self._styles.get("section_header_height", 7)
        sub_h = self._styles.get("header_height", 8)
        row_h = self._styles.get("row_height", 6.5)
        method_hdr_h = self._styles.get("method_header_height", 7)

        sub_ratios = [sc["width"] for sc in sub_columns]
        ratio_sum = sum(sub_ratios)
        sub_widths = [r / ratio_sum * col_w for r in sub_ratios]

        for ci in range(n_cols):
            col_left = cx + ci * (col_w + gap)
            col_right = col_left + col_w

            # 栏边框
            c.setLineWidth(0.4)
            c.line(col_left * mm, col_top * mm, col_right * mm, col_top * mm)
            c.line(col_left * mm, col_bottom * mm, col_right * mm, col_bottom * mm)
            c.line(col_left * mm, col_bottom * mm, col_left * mm, col_top * mm)
            c.line(col_right * mm, col_bottom * mm, col_right * mm, col_top * mm)

            if ci >= len(page_cols):
                continue

            blocks = page_cols[ci]
            cur_y = col_top

            # 子列表头（每栏顶部）
            c.setLineWidth(0.25)
            c.line(col_left * mm, (cur_y - sub_h) * mm,
                   col_right * mm, (cur_y - sub_h) * mm)
            c.setFont(self._font_name, self._font_size_body * mm)
            sub_x = col_left
            for si, sc in enumerate(sub_columns):
                c.drawString((sub_x + 1) * mm,
                             (cur_y - sub_h * 0.6) * mm, sc["header"])
                if si < len(sub_columns) - 1:
                    c.line((sub_x + sub_widths[si]) * mm, cur_y * mm,
                           (sub_x + sub_widths[si]) * mm, (cur_y - sub_h) * mm)
                sub_x += sub_widths[si]
            c.line(col_left * mm, cur_y * mm, col_left * mm, (cur_y - sub_h) * mm)
            c.line(col_right * mm, cur_y * mm, col_right * mm, (cur_y - sub_h) * mm)
            cur_y -= sub_h

            for block in blocks:
                if block["type"] == "section_header":
                    c.setLineWidth(0.25)
                    c.line(col_left * mm, (cur_y - section_h) * mm,
                           col_right * mm, (cur_y - section_h) * mm)
                    c.setFont(self._font_name, self._font_size_header * mm)
                    c.drawString((col_left + 1) * mm,
                                 (cur_y - section_h * 0.6) * mm,
                                 block["title"])
                    cur_y -= section_h

                elif block["type"] == "method":
                    method = block["data"]
                    layers = method.get("layers", [])
                    n_layers = len(layers) if layers else 1
                    total_mh = method_hdr_h + n_layers * row_h
                    method_bottom = cur_y - total_mh

                    sub_x = col_left

                    # 编号
                    c.setLineWidth(0.13)
                    c.line(sub_x * mm, cur_y * mm,
                           (sub_x + sub_widths[0]) * mm, cur_y * mm)
                    c.line(sub_x * mm, method_bottom * mm,
                           (sub_x + sub_widths[0]) * mm, method_bottom * mm)
                    c.line(sub_x * mm, method_bottom * mm, sub_x * mm, cur_y * mm)
                    c.line((sub_x + sub_widths[0]) * mm, method_bottom * mm,
                           (sub_x + sub_widths[0]) * mm, cur_y * mm)
                    c.setFont(self._font_name, self._font_size_body * mm)
                    id_text = method.get("id", "")
                    c.drawString((sub_x + 1) * mm,
                                 ((cur_y + method_bottom) / 2) * mm, id_text)
                    sub_x += sub_widths[0]

                    # 构造层次
                    c.line((sub_x + sub_widths[1]) * mm, method_bottom * mm,
                           (sub_x + sub_widths[1]) * mm, cur_y * mm)
                    c.line(sub_x * mm, cur_y * mm,
                           (sub_x + sub_widths[1]) * mm, cur_y * mm)
                    layer_y = cur_y
                    for li, layer in enumerate(layers):
                        layer_bottom = layer_y - row_h
                        if li < len(layers) - 1:
                            c.setLineWidth(1.0)
                        else:
                            c.setLineWidth(0.13)
                        c.line(sub_x * mm, layer_bottom * mm,
                               (sub_x + sub_widths[1]) * mm, layer_bottom * mm)
                        c.setLineWidth(0.13)
                        order = layer.get("order", li + 1)
                        material = layer.get("material", "")
                        thickness = layer.get("thickness", "")
                        if thickness and thickness != "-":
                            layer_text = f"{order}. {material}（{thickness}）"
                        else:
                            layer_text = f"{order}. {material}"
                        c.setFont(self._font_name, self._font_size_body * mm)
                        c.drawString((sub_x + 1) * mm,
                                     (layer_bottom + row_h * 0.3) * mm,
                                     layer_text[:30])
                        layer_y = layer_bottom
                    sub_x += sub_widths[1]

                    # 使用范围
                    c.setLineWidth(0.13)
                    c.line(sub_x * mm, cur_y * mm,
                           (sub_x + sub_widths[2]) * mm, cur_y * mm)
                    c.line(sub_x * mm, method_bottom * mm,
                           (sub_x + sub_widths[2]) * mm, method_bottom * mm)
                    c.line((sub_x + sub_widths[2]) * mm, method_bottom * mm,
                           (sub_x + sub_widths[2]) * mm, cur_y * mm)
                    c.setFont(self._font_name, self._font_size_body * mm)
                    c.drawString((sub_x + 1) * mm,
                                 ((cur_y + method_bottom) / 2) * mm,
                                 method.get("usage", "")[:20])
                    sub_x += sub_widths[2]

                    # 备注
                    c.line(sub_x * mm, cur_y * mm,
                           (sub_x + sub_widths[3]) * mm, cur_y * mm)
                    c.line(sub_x * mm, method_bottom * mm,
                           (sub_x + sub_widths[3]) * mm, method_bottom * mm)
                    c.line((sub_x + sub_widths[3]) * mm, method_bottom * mm,
                           (sub_x + sub_widths[3]) * mm, cur_y * mm)
                    c.setFont(self._font_name, self._font_size_body * mm)
                    c.drawString((sub_x + 1) * mm,
                                 ((cur_y + method_bottom) / 2) * mm,
                                 method.get("notes", "")[:15])

                    cur_y = method_bottom
