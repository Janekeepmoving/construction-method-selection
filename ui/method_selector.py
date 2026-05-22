# -*- coding: utf-8 -*-
"""做法选择面板 —— 树形结构展示部位→做法类型→做法列表，支持多选与预览。"""

import tkinter as tk
from tkinter import ttk


class MethodSelector(ttk.Frame):
    """部位 → 做法类型 → 做法列表 三级选择面板。

    使用 Treeview 展示结构，右侧显示选中做法的构造层次预览。
    用户可在此面板中选择/取消做法。
    """

    def __init__(self, parent, library, selection_manager, on_selection_changed=None):
        super().__init__(parent)
        self._lib = library
        self._sel_mgr = selection_manager
        self._on_changed = on_selection_changed

        self._build_ui()
        self._populate_tree()

    def _build_ui(self):
        """构建双栏布局：左侧树 + 右侧层次预览。"""
        # 左侧树
        left = ttk.LabelFrame(self, text="做法选择", padding=3)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 部位选择
        part_frame = ttk.Frame(left)
        part_frame.pack(fill=tk.X, pady=3)
        ttk.Label(part_frame, text="建筑部位:").pack(side=tk.LEFT)
        self._part_var = tk.StringVar()
        self._part_combo = ttk.Combobox(
            part_frame, textvariable=self._part_var,
            state="readonly", width=14)
        self._part_combo.pack(side=tk.LEFT, padx=5)
        self._part_combo.bind("<<ComboboxSelected>>", self._on_part_changed)

        # 做法类型选择
        type_frame = ttk.Frame(left)
        type_frame.pack(fill=tk.X, pady=3)
        ttk.Label(type_frame, text="做法类型:").pack(side=tk.LEFT)
        self._type_var = tk.StringVar()
        self._type_combo = ttk.Combobox(
            type_frame, textvariable=self._type_var,
            state="readonly", width=14)
        self._type_combo.pack(side=tk.LEFT, padx=5)
        self._type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # 做法列表
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self._method_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED,
            height=12, exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=self._method_listbox.yview)
        self._method_listbox.configure(yscrollcommand=scrollbar.set)
        self._method_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._method_listbox.bind("<<ListboxSelect>>", self._on_method_selected)

        # 操作按钮
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="添加选中做法 →",
                   command=self._add_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="移除已选",
                   command=self._remove_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="清空全部",
                   command=self._clear_all).pack(side=tk.LEFT, padx=3)

        # 右侧：已选做法及预览
        right = ttk.LabelFrame(self, text="已选做法清单", padding=3)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self._selected_tree = ttk.Treeview(
            right, columns=("type", "name"),
            show="tree headings", height=16)
        self._selected_tree.heading("#0", text="部位")
        self._selected_tree.heading("type", text="类型")
        self._selected_tree.heading("name", text="做法名称")
        self._selected_tree.column("#0", width=70)
        self._selected_tree.column("type", width=80)
        self._selected_tree.column("name", width=180)
        self._selected_tree.pack(fill=tk.BOTH, expand=True)

        ttk.Button(right, text="撤销 (Ctrl+Z)", command=self._undo).pack(
            side=tk.LEFT, padx=5, pady=2)
        ttk.Button(right, text="重做 (Ctrl+Y)", command=self._redo).pack(
            side=tk.LEFT, padx=5, pady=2)

    # ---------- 数据填充 ----------

    def _populate_tree(self):
        """初始化部位下拉框。"""
        parts = self._lib.get_parts()
        self._part_combo["values"] = parts
        if parts:
            self._part_combo.current(0)
            self._on_part_changed()

    def _on_part_changed(self, event=None):
        """部位变更时更新做法类型下拉框。"""
        part = self._part_var.get()
        types = self._lib.get_method_types(part)
        self._type_combo["values"] = types
        if types:
            self._type_combo.current(0)
            self._on_type_changed()

    def _on_type_changed(self, event=None):
        """做法类型变更时更新做法列表。"""
        part = self._part_var.get()
        mtype = self._type_var.get()
        methods = self._lib.get_methods(part, mtype)
        self._method_listbox.delete(0, tk.END)
        for m in methods:
            self._method_listbox.insert(tk.END,
                                         f"[{m['id']}] {m['name']}")

    def _on_method_selected(self, event=None):
        """列表选中时在右侧预览层次（可选触发）。"""
        pass  # 层次预览由主窗口连接

    # ---------- 操作 ----------

    def _add_selected(self):
        """将列表中选中的做法加入选择集。"""
        part = self._part_var.get()
        mtype = self._type_var.get()
        methods = self._lib.get_methods(part, mtype)

        selected_indices = self._method_listbox.curselection()
        for idx in selected_indices:
            if idx < len(methods):
                self._sel_mgr.add_selection(part, mtype, methods[idx])

        self._refresh_selected_tree()
        if self._on_changed:
            self._on_changed()

    def _remove_selected(self):
        """移除已选树中选中的做法。"""
        sel = self._selected_tree.selection()
        for item in sel:
            parent = self._selected_tree.parent(item)
            if parent:
                part = self._selected_tree.item(parent, "text")
                mtype = self._selected_tree.item(item, "values")[0]
                name = self._selected_tree.item(item, "values")[1]
                methods = self._sel_mgr.get_selected_methods(part, mtype)
                for m in methods:
                    if m.get("name") == name:
                        self._sel_mgr.remove_selection(part, mtype, m["id"])
                        break
        self._refresh_selected_tree()
        if self._on_changed:
            self._on_changed()

    def _clear_all(self):
        self._sel_mgr.clear_all()
        self._refresh_selected_tree()
        if self._on_changed:
            self._on_changed()

    def _undo(self):
        if self._sel_mgr.undo():
            self._refresh_selected_tree()
            if self._on_changed:
                self._on_changed()

    def _redo(self):
        if self._sel_mgr.redo():
            self._refresh_selected_tree()
            if self._on_changed:
                self._on_changed()

    # ---------- 刷新已选树 ----------

    def _refresh_selected_tree(self):
        """刷新右侧已选做法树。"""
        self._selected_tree.delete(*self._selected_tree.get_children())
        all_sel = self._sel_mgr.get_all_selections()
        for part, types in all_sel.items():
            part_node = self._selected_tree.insert(
                "", tk.END, text=part, open=True)
            for mtype, methods in types.items():
                for m in methods:
                    self._selected_tree.insert(
                        part_node, tk.END,
                        values=(mtype, m.get("name", "")),
                        text="")

    def get_selected_method_detail(self):
        """返回右侧树中当前选中的做法详情（供外部预览层次）。"""
        sel = self._selected_tree.selection()
        if not sel:
            return None
        item = sel[0]
        parent = self._selected_tree.parent(item)
        if not parent:
            return None
        part = self._selected_tree.item(parent, "text")
        values = self._selected_tree.item(item, "values")
        if not values:
            return None
        mtype, name = values[0], values[1]
        methods = self._sel_mgr.get_selected_methods(part, mtype)
        for m in methods:
            if m.get("name") == name:
                return part, mtype, m
        return None
