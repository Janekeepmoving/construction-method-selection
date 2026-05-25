# -*- coding: utf-8 -*-
"""表格预览面板 —— 生成前预览建筑构造做法表（流式 5 栏布局）。"""

import tkinter as tk
from tkinter import ttk


class PreviewPanel(ttk.LabelFrame):
    """表格数据预览面板。"""

    def __init__(self, parent):
        super().__init__(parent, text="表格预览（流式5栏布局）", padding=5)
        self._frame, self._text = self._create_text_area()

    def _create_text_area(self):
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(frame, wrap=tk.NONE, font=("Consolas", 9),
                       width=90, height=30)
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
        if not selections or all(
            not methods for part_data in selections.values()
            for methods in part_data.values()
        ):
            self._text.delete("1.0", tk.END)
            self._text.insert("1.0", "（暂无选择，请在左侧添加做法）")
            return

        table_data = table_builder.build_method_table(selections)
        self._show_table_preview(self._text, table_data)

    def _show_table_preview(self, text_widget, table_data: dict):
        text_widget.delete("1.0", tk.END)

        lines = []
        lines.append(f"【{table_data['title']}】  流式5栏布局")
        sections = table_data.get("sections", [])
        total_methods = sum(len(s["methods"]) for s in sections)
        non_empty = sum(1 for s in sections if s["methods"])
        lines.append(f"共 {non_empty} 个非空做法类型, {total_methods} 条做法")
        lines.append("")

        # 按顺序显示所有 section
        for sec in sections:
            methods = sec.get("methods", [])
            indicator = "  " if methods else "(空)"
            lines.append(f"{indicator} {sec['section_title']}  "
                         f"（{len(methods)} 条做法）")
            if not methods:
                continue
            for m in methods[:3]:  # 每 section 只显示前 3 条
                layers = m.get("layers", [])
                n = len(layers)
                lines.append(f"    [{m['id']}] {m.get('name', '')[:25]} "
                             f"({n}层)")
                for layer in layers[:2]:  # 每做法只显示前 2 层
                    mat = layer.get("material", "")[:25]
                    thick = layer.get("thickness", "")
                    if thick and thick != "-":
                        lines.append(f"         {layer.get('order','')}. {mat} ({thick})")
                    else:
                        lines.append(f"         {layer.get('order','')}. {mat}")
                if len(layers) > 2:
                    lines.append(f"         ... 共 {len(layers)} 层")
            if len(methods) > 3:
                lines.append(f"    ... 共 {len(methods)} 条做法")
            lines.append("")

        text_widget.insert("1.0", "\n".join(lines))
