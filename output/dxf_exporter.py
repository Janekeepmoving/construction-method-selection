# -*- coding: utf-8 -*-
"""DXF 图纸输出模块 —— 流式 5 栏布局，按做法类型顺序从上到下、从左到右排版。"""

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
import os

from .title_block import PageFrame


class DXFExporter:
    """流式 5 栏布局 DXF 输出。"""

    LW = {"thick": 40, "medium": 25, "thin": 13, "heavy": 100}

    def __init__(self, settings: dict, table_styles: dict):
        self._settings = settings
        self._styles = table_styles
        self._font_name = settings["fonts"]["body"]["name"]
        self._font_size_body = settings["fonts"]["body"]["size"]
        self._font_size_header = settings["fonts"]["header"]["size"]
        self._font_size_title = settings["fonts"]["title"]["size"]
        self._pads = table_styles.get("cell_padding",
                                       {"horizontal": 1.0, "vertical": 0.5})
        self._layer_sep_wt = table_styles.get("layer_separator_weight", 1.0)

    def export(self, table_data: dict, project_info,
               output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        pf = PageFrame(self._settings)
        doc = ezdxf.new(units=units.MM)
        doc.units = units.MM
        msp = doc.modelspace()
        self._setup_layers(doc)

        self._draw_frame(msp, pf)

        pages = self._paginate_flow(table_data, pf)
        base, ext = os.path.splitext(output_path)

        for page_idx, page_cols in enumerate(pages):
            page_path = output_path if len(pages) == 1 else \
                f"{base}_p{page_idx + 1}{ext}"

            if page_idx == 0 and len(pages) == 1:
                doc_page, msp_page = doc, msp
            else:
                doc_page = ezdxf.new(units=units.MM)
                doc_page.units = units.MM
                msp_page = doc_page.modelspace()
                self._setup_layers(doc_page)
                pf2 = PageFrame(self._settings)
                self._draw_frame(msp_page, pf2)

            self._draw_page(msp_page, page_cols, table_data["sub_columns"],
                            pf, page_idx + 1, len(pages))

            if len(pages) > 1:
                doc_page.saveas(page_path)

        doc.saveas(output_path if len(pages) == 1 else output_path)
        return output_path if len(pages) == 1 else output_path

    # ---------- 图层 ----------

    def _setup_layers(self, doc):
        for name, lw in [("FRAME", self.LW["thin"]),
                          ("TABLE-BORDER", self.LW["thick"]),
                          ("TABLE-HEADER", self.LW["medium"]),
                          ("TABLE-CELL", self.LW["thin"]),
                          ("TABLE-LAYER-SEP", self.LW["heavy"]),
                          ("TEXT", self.LW["thin"])]:
            layer = doc.layers.new(name)
            layer.lineweight = lw

        # SHX 字体：引用 AutoCAD 字体文件名
        try:
            doc.styles.new("HzTXT", dxfattribs={"font": "HzTXT.shx"})
        except Exception:
            pass

    # ---------- 页面外框 ----------

    def _draw_frame(self, msp, pf: PageFrame):
        for (x1, y1), (x2, y2) in pf.frame_lines():
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "FRAME"})

    # ---------- 流式分页 ----------

    def _paginate_flow(self, table_data: dict, pf: PageFrame) -> list:
        """流式布局：将做法按顺序填入 5 栏，从上到下、从左到右。

        返回: pages 列表，每个 page 是 5 个 column 的列表，
              每 column 是 block 列表。
        """
        sections = table_data.get("sections", [])
        section_h = self._styles.get("section_header_height", 7)
        row_h = self._styles.get("row_height", 6.5)
        method_hdr_h = self._styles.get("method_header_height", 7)

        # 展平为 block 列表
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
                        # 节标题：确保后面至少跟一个做法，避免孤行
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
                        # 栏为空且放不下 → 强制放入
                        if not page_cols[ci]:
                            page_cols[ci].append(block)
                            col_cursors[ci] -= block["height"]
                            block_idx += 1
                        break

            pages.append(page_cols)

        return pages

    # ---------- 页面绘制 ----------

    def _draw_page(self, msp, page_cols: list, sub_columns: list,
                   pf: PageFrame, page_num: int, total_pages: int):
        """绘制一页完整内容（5 栏流式布局）。"""
        cx, cy, cw, ch = pf.content_rect
        n_cols = 5
        gap = self._styles.get("column_gap", 2)
        col_w = (cw - (n_cols - 1) * gap) / n_cols

        title_h = self._styles.get("title_height", 12)

        title_text = f"{self._styles['table_type']['name']}（第{page_num}页/共{total_pages}页）" \
            if total_pages > 1 else self._styles["table_type"]["name"]
        self._add_title(msp, title_text, cx, cy + ch - title_h, cw, title_h)

        # 标题下横线
        self._hline(msp, cx, cx + cw, cy + ch - title_h, "TABLE-BORDER")

        col_top = cy + ch - title_h
        col_bottom = cy

        for ci in range(n_cols):
            col_left = cx + ci * (col_w + gap)
            col_right = col_left + col_w

            # 栏外框
            self._vline(msp, col_left, col_bottom, col_top, "TABLE-BORDER")
            self._vline(msp, col_right, col_bottom, col_top, "TABLE-BORDER")
            self._hline(msp, col_left, col_right, col_bottom, "TABLE-BORDER")

            if ci < len(page_cols):
                self._draw_column(msp, page_cols[ci], sub_columns,
                                  col_left, col_bottom, col_w, col_top)

    def _draw_column(self, msp, blocks: list, sub_columns: list,
                     col_left: float, col_bottom: float,
                     col_w: float, col_top: float):
        """绘制一栏内的所有 block（section_header + method）。"""
        section_h = self._styles.get("section_header_height", 7)
        sub_h = self._styles.get("header_height", 8)
        row_h = self._styles.get("row_height", 6.5)
        method_hdr_h = self._styles.get("method_header_height", 7)

        # 子列宽度
        sub_ratios = [sc["width"] for sc in sub_columns]
        ratio_sum = sum(sub_ratios)
        sub_widths = [r / ratio_sum * col_w for r in sub_ratios]

        cur_y = col_top

        # 子列表头（每栏顶部）
        self._hline(msp, col_left, col_left + col_w, cur_y - sub_h, "TABLE-HEADER")
        sub_x = col_left
        for si, sc in enumerate(sub_columns):
            sx = sub_x + sub_widths[si] / 2
            self._add_text_centered(msp, sc["header"], sx,
                                     cur_y - sub_h / 2,
                                     sub_widths[si], sub_h,
                                     self._font_size_body, "HzTXT")
            if si < len(sub_columns) - 1:
                self._vline(msp, sub_x + sub_widths[si], cur_y, cur_y - sub_h,
                           "TABLE-HEADER")
            sub_x += sub_widths[si]
        self._vline(msp, col_left, cur_y, cur_y - sub_h, "TABLE-HEADER")
        self._vline(msp, col_left + col_w, cur_y, cur_y - sub_h, "TABLE-HEADER")
        cur_y -= sub_h

        # 遍历 block 列表
        for block in blocks:
            if block["type"] == "section_header":
                self._hline(msp, col_left, col_left + col_w,
                           cur_y - section_h, "TABLE-HEADER")
                self._add_text_centered(msp, block["title"],
                                         col_left + col_w / 2,
                                         cur_y - section_h / 2,
                                         col_w, section_h,
                                         self._font_size_header, "HzTXT")
                cur_y -= section_h

            elif block["type"] == "method":
                method = block["data"]
                layers = method.get("layers", [])
                n_layers = len(layers) if layers else 1
                total_mh = method_hdr_h + n_layers * row_h
                method_bottom = cur_y - total_mh

                sub_x = col_left

                # === 编号列 (col 0) ===
                self._vline(msp, sub_x, method_bottom, cur_y, "TABLE-CELL")
                self._vline(msp, sub_x + sub_widths[0], method_bottom, cur_y,
                           "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[0], cur_y, "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[0], method_bottom,
                           "TABLE-CELL")
                self._add_text_centered(msp, method.get("id", ""),
                                         sub_x + sub_widths[0] / 2,
                                         (cur_y + method_bottom) / 2,
                                         sub_widths[0], total_mh,
                                         self._font_size_body, "HzTXT")
                sub_x += sub_widths[0]

                # === 构造层次列 (col 1) ===
                self._vline(msp, sub_x + sub_widths[1], method_bottom, cur_y,
                           "TABLE-CELL")
                # 做法名称（小字，在构造层次顶部）
                name_h = min(row_h, total_mh - n_layers * row_h)
                name_bottom = cur_y - name_h
                self._hline(msp, sub_x, sub_x + sub_widths[1], name_bottom, "TABLE-CELL")
                self._add_text_cell(msp, method.get("name", ""),
                                     sub_x, name_bottom,
                                     sub_widths[1], name_h,
                                     self._font_size_body, "HzTXT")
                layer_y = name_bottom
                for li, layer in enumerate(layers):
                    layer_top = layer_y
                    layer_bottom = layer_y - row_h
                    if li < len(layers) - 1:
                        self._hline(msp, sub_x, sub_x + sub_widths[1],
                                   layer_bottom, "TABLE-LAYER-SEP")
                    else:
                        self._hline(msp, sub_x, sub_x + sub_widths[1],
                                   layer_bottom, "TABLE-CELL")
                    order = layer.get("order", li + 1)
                    material = layer.get("material", "")
                    thickness = layer.get("thickness", "")
                    if thickness and thickness != "-":
                        layer_text = f"{order}. {material}（{thickness}）"
                    else:
                        layer_text = f"{order}. {material}"
                    self._add_text_cell(msp, layer_text,
                                         sub_x, layer_bottom,
                                         sub_widths[1], row_h,
                                         self._font_size_body, "HzTXT")
                    layer_y = layer_bottom
                self._hline(msp, sub_x, sub_x + sub_widths[1], cur_y, "TABLE-CELL")
                sub_x += sub_widths[1]

                # === 使用范围列 (col 2) ===
                self._vline(msp, sub_x + sub_widths[2], method_bottom, cur_y,
                           "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[2], cur_y, "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[2], method_bottom,
                           "TABLE-CELL")
                self._add_text_centered(msp, method.get("usage", ""),
                                         sub_x + sub_widths[2] / 2,
                                         (cur_y + method_bottom) / 2,
                                         sub_widths[2], total_mh,
                                         self._font_size_body, "HzTXT")
                sub_x += sub_widths[2]

                # === 备注列 (col 3) ===
                self._vline(msp, sub_x + sub_widths[3], method_bottom, cur_y,
                           "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[3], cur_y, "TABLE-CELL")
                self._hline(msp, sub_x, sub_x + sub_widths[3], method_bottom,
                           "TABLE-CELL")
                self._add_text_centered(msp, method.get("notes", ""),
                                         sub_x + sub_widths[3] / 2,
                                         (cur_y + method_bottom) / 2,
                                         sub_widths[3], total_mh,
                                         self._font_size_body, "HzTXT")

                cur_y = method_bottom

    # ---------- 线条辅助 ----------

    def _hline(self, msp, x1, x2, y, layer):
        msp.add_line((x1, y), (x2, y), dxfattribs={"layer": layer})

    def _vline(self, msp, x, y1, y2, layer):
        msp.add_line((x, y1), (x, y2), dxfattribs={"layer": layer})

    # ---------- 标题 ----------

    def _add_title(self, msp, text: str, tx: float, ty: float,
                   tw: float, th: float):
        msp.add_text(
            text,
            dxfattribs={"layer": "TEXT", "height": self._font_size_title,
                        "width": 0.7, "style": "HzTXT"},
        ).set_placement((tx + tw / 2, ty + th / 2),
                         align=TextEntityAlignment.MIDDLE_CENTER)

    # ---------- 文字辅助 ----------

    def _add_text_centered(self, msp, text: str, cx: float, cy: float,
                            cell_w: float, cell_h: float, font_size: float,
                            style_name: str):
        if not text:
            return
        fs = font_size
        max_w = cell_w - 2 * self._pads["horizontal"]
        char_w = fs * 0.7
        max_chars = int(max_w / char_w) if char_w > 0 else 20
        lines = str(text).split("\n")
        display = lines[0][:max_chars]
        if len(lines) > 1:
            second = lines[1][:max_chars] if len(lines) > 1 else ""
            display = display + "\n" + second

        msp.add_text(
            display,
            dxfattribs={"layer": "TEXT", "height": fs,
                        "width": 0.7, "style": style_name},
        ).set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)

    def _add_text_cell(self, msp, text: str, x: float, y: float,
                        w: float, h: float, font_size: float,
                        style_name: str):
        if not text:
            return
        fs = font_size
        pad_h = self._pads["horizontal"]
        max_w = w - 2 * pad_h
        char_w = fs * 0.7
        max_chars = int(max_w / char_w) if char_w > 0 else 20
        display = str(text)[:max_chars]

        msp.add_text(
            display,
            dxfattribs={"layer": "TEXT", "height": fs,
                        "width": 0.7, "style": style_name},
        ).set_placement((x + pad_h, y + h * 0.25),
                         align=TextEntityAlignment.MIDDLE_LEFT)
