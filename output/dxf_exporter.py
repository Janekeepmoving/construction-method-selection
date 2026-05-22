# -*- coding: utf-8 -*-
"""DXF 图纸输出模块 —— 使用 ezdxf 将表格与图框叠加输出为 DXF 文件。

图纸坐标系: 原点在左下角，X 向右，Y 向上，单位 mm。
图框外框从 (0,0) 到 (pw, ph)。
表格定位在内框内部，可跨页。
"""

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
from typing import Optional
import os

from .title_block import TitleBlock


class DXFExporter:
    """将表格数据与图框叠加，输出为 .dxf 文件。"""

    # 线宽映射
    LW = {"thick": 40, "medium": 25, "thin": 13}  # ezdxf 线宽以 1/100 mm 为单位

    def __init__(self, settings: dict, title_block_config: dict):
        self._settings = settings
        self._tb_config = title_block_config
        self._font_name = settings["fonts"]["body"]["name"]
        self._font_size_body = settings["fonts"]["body"]["size"]
        self._font_size_header = settings["fonts"]["header"]["size"]
        self._font_size_title = settings["fonts"]["title"]["size"]
        self._pads = settings.get("cell_padding", {"horizontal": 1.5, "vertical": 1.0})

    def export(self, table_data: dict, project_info, paper_size: str,
               output_path: str) -> str:
        """导出单张表格到 DXF 文件。

        Args:
            table_data: TableBuilder 产出的表格字典
            project_info: ProjectInfo 对象
            paper_size: "A2" 或 "A3"
            output_path: 输出文件路径 (.dxf)

        Returns:
            实际输出路径
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        tb = TitleBlock(self._tb_config, paper_size)
        doc = ezdxf.new(units=units.MM)
        doc.units = units.MM

        msp = doc.modelspace()
        self._setup_layers(doc)

        # ---- 绘制图框 ----
        self._draw_outer_frame(msp, tb)
        self._draw_inner_frame(msp, tb)
        self._draw_title_block(msp, tb)
        self._draw_info_area(msp, tb, project_info)

        # ---- 计算表格可用区域 ----
        usable = tb.inner_rect  # (x, y, w, h)
        margin = 10  # 表格距内框边距

        # ---- 绘制表格（可能跨页） ----
        actual_path = self._draw_table(msp, table_data, tb, usable, margin,
                                       project_info, output_path, doc)

        doc.saveas(actual_path)
        return actual_path

    # ---------- 图层设置 ----------

    def _setup_layers(self, doc):
        """创建线型分级图层。"""
        for name, lw in [("FRAME-OUTER", self.LW["thin"]),
                          ("FRAME-INNER", self.LW["thick"]),
                          ("TITLE-BLOCK", self.LW["medium"]),
                          ("TABLE-BORDER", self.LW["thick"]),
                          ("TABLE-HEADER", self.LW["medium"]),
                          ("TABLE-CELL", self.LW["thin"]),
                          ("TEXT", self.LW["thin"])]:
            layer = doc.layers.new(name)
            layer.lineweight = lw

        # 文字样式: 仿宋
        style_name = self._font_name.replace("_", "")
        try:
            doc.styles.new(style_name, dxfattribs={"font": self._font_name + ".ttf"})
        except Exception:
            # 如果指定字体不可用，使用默认
            pass

    # ---------- 图框绘制 ----------

    def _draw_outer_frame(self, msp, tb: TitleBlock):
        """外框细线。"""
        for (x1, y1), (x2, y2) in tb.outer_frame_lines():
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "FRAME-OUTER"})

    def _draw_inner_frame(self, msp, tb: TitleBlock):
        """内框粗线。"""
        for (x1, y1), (x2, y2) in tb.inner_frame_lines():
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "FRAME-INNER"})

    def _draw_title_block(self, msp, tb: TitleBlock):
        """标题栏。"""
        for (x1, y1), (x2, y2) in tb.title_block_lines():
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "TITLE-BLOCK"})
        # 标题栏文字
        for tinfo in tb.title_block_texts():
            self._add_text_centered(msp, tinfo["text"],
                                     tinfo["x"], tinfo["y"],
                                     tinfo["width"], tinfo["height"],
                                     self._font_size_body)

        # 标题横条
        ts = tb.ts_cfg
        if ts:
            tx = ts.get("x_offset", 0)
            ty = ts.get("y_offset", 0)
            tw = ts.get("width", 0)
            th = ts.get("height", 0)
            msp.add_line((tx, ty), (tx + tw, ty), dxfattribs={"layer": "TITLE-BLOCK"})
            msp.add_line((tx, ty + th), (tx + tw, ty + th),
                         dxfattribs={"layer": "TITLE-BLOCK"})

    def _draw_info_area(self, msp, tb: TitleBlock, project_info):
        """项目信息区域与项目数据填充。"""
        info = tb.info_cfg
        if not info:
            return
        # 外框
        for (x1, y1), (x2, y2) in tb.info_area_lines():
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "TITLE-BLOCK"})

        # 项目信息文字
        proj = project_info
        field_map = {
            "项目名称": proj.project_name,
            "图纸名称": proj.drawing_name,
            "图号": proj.drawing_number,
        }
        for field in info.get("fields", []):
            label = field["label"]
            val = field.get("value", field_map.get(label, ""))
            fx = field["x"]
            fy = info["y_top"] - info["height"] / 2
            fw = field["width"]
            display = f"{label}: {val}" if val else label
            self._add_text_centered(msp, display, fx + fw / 2, fy,
                                     fw, info["height"], self._font_size_body)

    # ---------- 表格绘制 ----------

    def _draw_table(self, msp, table_data: dict, tb: TitleBlock,
                    usable: tuple, margin: float, project_info,
                    output_path: str, doc) -> str:
        """在可用区域内绘制表格，内容超出时自动分页。"""
        ux, uy, uw, uh = usable
        table_x = ux + margin
        table_y = uy + margin
        table_w = uw - 2 * margin
        max_table_h = uh - 2 * margin

        # 列宽：按配置比例缩放至可用宽度
        cols = table_data["columns"]
        col_ratios = [c["width"] for c in cols]
        ratio_sum = sum(col_ratios)
        col_widths = [r / ratio_sum * table_w for r in col_ratios]

        th = table_data["title_height"]
        hh = table_data["header_height"]
        rh = table_data["row_height"]

        title_h = th
        header_h = hh

        # 将行按高度分组，确定每页容纳行数
        data_rows = table_data["rows"]
        first_page_overhead = title_h + header_h + 10
        page_overhead = header_h + 10
        row_height = rh

        # 分组
        pages = self._paginate_rows(data_rows, row_height,
                                     max_table_h, first_page_overhead,
                                     page_overhead)

        # 为每页生成文件
        base, ext = os.path.splitext(output_path)
        for page_idx, page_rows in enumerate(pages):
            page_path = output_path if len(pages) == 1 else \
                f"{base}_p{page_idx + 1}{ext}"

            if page_idx == 0 and len(pages) == 1:
                doc2 = doc
                msp2 = msp
            else:
                doc2 = ezdxf.new(units=units.MM)
                doc2.units = units.MM
                msp2 = doc2.modelspace()
                self._setup_layers(doc2)
                tb2 = TitleBlock(self._tb_config, tb.size)
                self._draw_outer_frame(msp2, tb2)
                self._draw_inner_frame(msp2, tb2)
                self._draw_title_block(msp2, tb2)
                self._draw_info_area(msp2, tb2, project_info)

            # 绘制本页表格
            show_title = (page_idx == 0)
            page_table_h = (title_h if show_title else 0) + header_h + \
                len(page_rows) * row_height
            start_y = table_y + max_table_h - page_table_h - 5

            self._draw_table_content(msp2, col_widths, cols,
                                      table_x, start_y,
                                      page_rows, show_title,
                                      table_data["title"],
                                      title_h, header_h, row_height,
                                      page_idx + 1, len(pages))

            if len(pages) > 1:
                doc2.saveas(page_path)

        return output_path if len(pages) == 1 else output_path

    def _paginate_rows(self, rows: list, row_h: float,
                        max_h: float, first_overhead: float,
                        other_overhead: float) -> list:
        """将数据行分配到多个页面。"""
        pages = []
        remaining = list(rows)
        first_page = True
        while remaining:
            capacity = int((max_h - (first_overhead if first_page else other_overhead))
                           // row_h)
            capacity = max(capacity, 1)
            pages.append(remaining[:capacity])
            remaining = remaining[capacity:]
            first_page = False
        return pages

    def _draw_table_content(self, msp, col_widths: list, cols: list,
                             table_x: float, start_y: float,
                             rows: list, show_title: bool,
                             title: str, title_h: float,
                             header_h: float, row_h: float,
                             page_num: int, total_pages: int):
        """绘制一张表的内容（不含图框）。"""
        pad_h = self._pads["horizontal"]
        pad_v = self._pads["vertical"]

        # 列累计 X
        col_x = []
        cx = table_x
        for w in col_widths:
            col_x.append(cx)
            cx += w
        table_w = sum(col_widths)
        end_x = table_x + table_w

        # 当前 Y 位置（从上往下画）
        cur_y = start_y

        # ---- 标题行 ----
        if show_title:
            title_display = f"{title}  (第{page_num}页/共{total_pages}页)" \
                if total_pages > 1 else title
            msp.add_line((table_x, cur_y), (end_x, cur_y),
                         dxfattribs={"layer": "TABLE-BORDER"})
            msp.add_line((table_x, cur_y + title_h), (end_x, cur_y + title_h),
                         dxfattribs={"layer": "TABLE-BORDER"})
            msp.add_line((table_x, cur_y), (table_x, cur_y + title_h),
                         dxfattribs={"layer": "TABLE-BORDER"})
            msp.add_line((end_x, cur_y), (end_x, cur_y + title_h),
                         dxfattribs={"layer": "TABLE-BORDER"})
            self._add_text_centered(msp, title_display,
                                     table_x + table_w / 2,
                                     cur_y + title_h / 2,
                                     table_w, title_h,
                                     self._font_size_title)
            cur_y += title_h

        # ---- 表头行 ----
        msp.add_line((table_x, cur_y), (end_x, cur_y),
                     dxfattribs={"layer": "TABLE-HEADER"})
        msp.add_line((table_x, cur_y + header_h), (end_x, cur_y + header_h),
                     dxfattribs={"layer": "TABLE-HEADER"})
        for ci, col in enumerate(cols):
            cx = col_x[ci]
            if ci < len(cols) - 1:
                msp.add_line((col_x[ci + 1], cur_y),
                             (col_x[ci + 1], cur_y + header_h),
                             dxfattribs={"layer": "TABLE-HEADER"})
            self._add_text_centered(msp, col["header"],
                                     cx + col_widths[ci] / 2,
                                     cur_y + header_h / 2,
                                     col_widths[ci], header_h,
                                     self._font_size_header)
        # 左边线
        msp.add_line((table_x, cur_y), (table_x, cur_y + header_h),
                     dxfattribs={"layer": "TABLE-HEADER"})
        msp.add_line((end_x, cur_y), (end_x, cur_y + header_h),
                     dxfattribs={"layer": "TABLE-HEADER"})
        cur_y += header_h

        # ---- 数据行 ----
        for ri, row in enumerate(rows):
            row_bottom = cur_y
            row_top = cur_y + row_h
            layer = "TABLE-HEADER" if row.get("type") == "group_header" else "TABLE-CELL"

            # 水平线
            msp.add_line((table_x, row_bottom), (end_x, row_bottom),
                         dxfattribs={"layer": layer})
            msp.add_line((table_x, row_top), (end_x, row_top),
                         dxfattribs={"layer": layer})
            # 竖线
            for ci in range(len(cols) + 1):
                lx = col_x[ci] if ci < len(cols) else end_x
                msp.add_line((lx, row_bottom), (lx, row_top),
                             dxfattribs={"layer": layer})

            # 单元格文字
            cells = row.get("cells", [])
            colspan = row.get("colspan", 1)
            if colspan > 1 and cells:
                # 合并单元格：文字跨多列居中
                merged_w = sum(col_widths[:colspan])
                self._add_text_centered(msp, cells[0],
                                         table_x + merged_w / 2,
                                         cur_y + row_h / 2,
                                         merged_w, row_h,
                                         self._font_size_body)
            else:
                for ci, cell_text in enumerate(cells):
                    if ci >= len(col_widths):
                        break
                    self._add_text_cell(msp, str(cell_text),
                                         col_x[ci], cur_y,
                                         col_widths[ci], row_h,
                                         self._font_size_body)

            cur_y += row_h

        # 表格底边加粗线
        msp.add_line((table_x, cur_y), (end_x, cur_y),
                     dxfattribs={"layer": "TABLE-BORDER"})
        # 左右外框
        msp.add_line((table_x, start_y + (title_h if show_title else 0)),
                     (table_x, cur_y), dxfattribs={"layer": "TABLE-BORDER"})
        msp.add_line((end_x, start_y + (title_h if show_title else 0)),
                     (end_x, cur_y), dxfattribs={"layer": "TABLE-BORDER"})

    # ---------- 文字辅助 ----------

    def _add_text_centered(self, msp, text: str, cx: float, cy: float,
                            cell_w: float, cell_h: float, font_size: float):
        """在单元格中心添加单行文字。"""
        if not text:
            return
        fs = font_size
        max_w = cell_w - 2 * self._pads["horizontal"]
        # 估算字符宽度 (仿宋字体宽高比约 0.7)
        char_w = fs * 0.7
        max_chars = int(max_w / char_w) if char_w > 0 else 20
        display = str(text)[:max_chars]

        msp.add_text(
            display,
            dxfattribs={
                "layer": "TEXT",
                "height": fs,
                "width": 0.7,
                "style": self._font_name.replace("_", ""),
            },
        ).set_placement(
            (cx, cy),
            align=TextEntityAlignment.MIDDLE_CENTER,
        )

    def _add_text_cell(self, msp, text: str, x: float, y: float,
                        w: float, h: float, font_size: float):
        """在数据单元格内添加文字（左对齐，留边距）。"""
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
            dxfattribs={
                "layer": "TEXT",
                "height": fs,
                "width": 0.7,
                "style": self._font_name.replace("_", ""),
            },
        ).set_placement(
            (x + pad_h, y + h / 2),
            align=TextEntityAlignment.MIDDLE_LEFT,
        )
