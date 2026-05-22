# -*- coding: utf-8 -*-
"""表格预览面板 —— 生成前预览三种表格的数据概览。"""

import tkinter as tk
from tkinter import ttk


class PreviewPanel(ttk.LabelFrame):
    """表格数据预览面板。

    展示生成的表格的行数、列数、关键摘要，供用户在出图前确认。
    """

    def __init__(self, parent):
        super().__init__(parent, text="表格预览", padding=5)

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # 三个 Tab
        self._tab1_frame, self._tab1_text = self._create_text_tab()
        self._tab2_frame, self._tab2_text = self._create_text_tab()
        self._tab3_frame, self._tab3_text = self._create_text_tab()

        self._notebook.add(self._tab1_frame, text="构造做法表")
        self._notebook.add(self._tab2_frame, text="装修一览表")
        self._notebook.add(self._tab3_frame, text="室内装修表")

    def _create_text_tab(self):
        """创建含多行文本显示的面板页，返回 (frame, text_widget)。"""
        frame = ttk.Frame(self._notebook)
        text = tk.Text(frame, wrap=tk.NONE, font=("Consolas", 9),
                       width=60, height=20)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL,
                                  command=text.xview)
        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                                  command=text.yview)
        text.configure(xscrollcommand=h_scroll.set,
                       yscrollcommand=v_scroll.set)

        text.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        return frame, text

    def update_preview(self, table_builder, selections: dict):
        """根据当前选择更新三个预览 Tab。"""
        if not selections or all(
            not methods for part_data in selections.values()
            for methods in part_data.values()
        ):
            for tab in [self._tab1_text, self._tab2_text, self._tab3_text]:
                tab.delete("1.0", tk.END)
                tab.insert("1.0", u"（暂无选择，请在左侧添加做法）")
            return

        # 构造做法表
        t1 = table_builder.build_method_table(selections)
        self._show_table_preview(self._tab1_text, t1)

        # 建筑装修一览表
        t2 = table_builder.build_decoration_summary(selections)
        self._show_table_preview(self._tab2_text, t2)

        # 室内装修一览表
        t3 = table_builder.build_interior_decoration(selections)
        self._show_table_preview(self._tab3_text, t3)

    def _show_table_preview(self, text_widget, table_data: dict):
        """在文本控件中以 ASCII 方式预览表格。"""
        text_widget.delete("1.0", tk.END)

        lines = []
        lines.append(f"【{table_data['title']}】")
        lines.append(f"列数: {len(table_data['columns'])}, "
                     f"数据行数: {len(table_data['rows'])}, "
                     f"总宽: {table_data['total_width']:.0f}mm, "
                     f"估算高: {table_data['total_height_estimate']:.0f}mm")
        lines.append("-" * 80)

        # 表头
        headers = [c["header"] for c in table_data["columns"]]
        lines.append(" | ".join(f"{h:^12s}" for h in headers))
        lines.append("-" * 80)

        # 数据行（只显示前 40 行预览）
        for i, row in enumerate(table_data["rows"][:40]):
            cells = row.get("cells", [])
            padded = []
            for j, cell in enumerate(cells):
                s = str(cell)[:12]
                padded.append(f"{s:<12s}")
            lines.append(" | ".join(padded))

        if len(table_data["rows"]) > 40:
            lines.append(f"... (共 {len(table_data['rows'])} 行，仅显示前 40 行)")

        text_widget.insert("1.0", "\n".join(lines))
