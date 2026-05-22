# -*- coding: utf-8 -*-
"""表格预览面板 —— 生成前预览 5 栏建筑构造做法表。"""

import tkinter as tk
from tkinter import ttk


class PreviewPanel(ttk.LabelFrame):
    """表格数据预览面板。"""

    def __init__(self, parent):
        super().__init__(parent, text="表格预览（5栏布局）", padding=5)
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
        lines.append(f"【{table_data['title']}】  5栏布局")
        total_methods = sum(len(c["methods"]) for c in table_data["columns"])
        lines.append(f"共 {len(table_data['columns'])} 栏, "
                     f"{total_methods} 条做法")
        lines.append("")

        # 显示每栏摘要
        for ci, col in enumerate(table_data["columns"]):
            methods = col.get("methods", [])
            lines.append(f"=== {col['section_title']} "
                         f"（{len(methods)} 条做法） ===")
            if not methods:
                lines.append("  （无）")
                continue
            for m in methods[:5]:  # 每栏只显示前 5 条
                layers = m.get("layers", [])
                n = len(layers)
                lines.append(f"  [{m['id']}] {m.get('name', '')[:20]} "
                             f"({n}层)")
                for layer in layers[:3]:  # 每做法只显示前 3 层
                    mat = layer.get("material", "")[:30]
                    thick = layer.get("thickness", "")
                    lines.append(f"       {layer.get('order','')}. {mat} "
                                 f"({thick})" if thick and thick != "-"
                                 else f"       {layer.get('order','')}. {mat}")
                if len(layers) > 3:
                    lines.append(f"       ... 共 {len(layers)} 层")
            if len(methods) > 5:
                lines.append(f"  ... 共 {len(methods)} 条做法")
            lines.append("")

        text_widget.insert("1.0", "\n".join(lines))
