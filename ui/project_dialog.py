# -*- coding: utf-8 -*-
"""项目信息对话框 —— 填写图框标题栏所需的项目信息。"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


class ProjectDialog(tk.Toplevel):
    """项目信息编辑对话框。

    提供项目名称、图纸名称、图号、设计人、日期、比例等字段的输入。
    """

    def __init__(self, parent, project_info):
        super().__init__(parent)
        self.title("项目信息设置")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._proj = project_info
        self.result = None  # 用户点击确定后设为 True

        self._build_ui()
        self._load_data()

        # 居中
        self.update_idletasks()
        pw = parent.winfo_width()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        self.geometry(f"+{px + pw // 2 - 240}+{py + 50}")

    def _build_ui(self):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("项目名称:", "project_name", 40),
            ("图纸名称:", "drawing_name", 40),
            ("图    号:", "drawing_number", 30),
            ("设计人:", "designer", 20),
            ("日    期:", "date", 20),
            ("比    例:", "scale", 20),
            ("图    别:", "drawing_type", 20),
            ("设计号:", "design_number", 30),
            ("审核人:", "reviewer", 20),
            ("审定人:", "approver", 20),
        ]

        self._entries = {}
        for i, (label, attr, width) in enumerate(fields):
            ttk.Label(frame, text=label, font=("", 10)).grid(
                row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(frame, textvariable=var, width=width)
            entry.grid(row=i, column=1, sticky=tk.W, pady=3, padx=(5, 0))
            self._entries[attr] = var

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(
            side=tk.LEFT, padx=10)

    def _load_data(self):
        """从 ProjectInfo 对象加载已有值。"""
        for attr, var in self._entries.items():
            val = getattr(self._proj, attr, "")
            var.set(str(val) if val else "")

    def _on_ok(self):
        """确认：保存回 ProjectInfo 并关闭。"""
        for attr, var in self._entries.items():
            setattr(self._proj, attr, var.get().strip())
        # 基本校验
        if not self._proj.project_name:
            messagebox.showwarning("提示", "项目名称不能为空")
            return
        if not self._proj.drawing_name:
            self._proj.drawing_name = "构造做法表"
        self.result = True
        self.destroy()
