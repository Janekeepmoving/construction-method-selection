# -*- coding: utf-8 -*-
"""构造层次编辑器 —— 预览选中做法的构造层次，支持调整顺序、修改内容。"""

import tkinter as tk
from tkinter import ttk, messagebox


class LayerEditor(ttk.LabelFrame):
    """编辑已选做法的构造层次。

    以表格形式展示做法各层（序号、材料、厚度、说明），
    支持上移/下移/编辑/删除/新增层次。
    """

    def __init__(self, parent, selection_manager, on_changed=None):
        super().__init__(parent, text="构造层次编辑", padding=5)
        self._sel_mgr = selection_manager
        self._on_changed = on_changed
        self._current_method = None  # (part, mtype, method_dict)

        self._build_ui()

    def _build_ui(self):
        """工具栏 + Treeview 表格。"""
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=3)

        ttk.Button(toolbar, text="上移 ↑", command=self._move_up).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="下移 ↓", command=self._move_down).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑层", command=self._edit_layer).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除层", command=self._delete_layer).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="新增层", command=self._add_layer).pack(
            side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(toolbar, text="保存修改",
                   command=self._save_changes).pack(side=tk.LEFT, padx=2)

        # 表格
        cols = ("序号", "材料及做法", "厚度(mm)", "备注")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        for c in cols:
            self._tree.heading(c, text=c)
        self._tree.column("序号", width=50, anchor=tk.CENTER)
        self._tree.column("材料及做法", width=280)
        self._tree.column("厚度(mm)", width=80, anchor=tk.CENTER)
        self._tree.column("备注", width=180)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                   command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------- 数据加载 ----------

    def load_method(self, part: str, mtype: str, method: dict):
        """加载一条做法到编辑器。"""
        self._current_method = (part, mtype, method)
        self._refresh_table()

    def _refresh_table(self):
        """刷新层次表格。"""
        self._tree.delete(*self._tree.get_children())
        if not self._current_method:
            return
        _, _, method = self._current_method
        for layer in method.get("layers", []):
            self._tree.insert("", tk.END, values=(
                layer.get("order", ""),
                layer.get("material", ""),
                layer.get("thickness", ""),
                layer.get("note", ""),
            ))

    # ---------- 层次操作 ----------

    def _move_up(self):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self._tree.index(item)
        if idx > 0:
            self._tree.move(item, "", idx - 1)
            self._tree.selection_set(item)

    def _move_down(self):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self._tree.index(item)
        children = self._tree.get_children()
        if idx < len(children) - 1:
            self._tree.move(item, "", idx + 1)
            self._tree.selection_set(item)

    def _edit_layer(self):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = list(self._tree.item(item, "values"))
        dialog = LayerEditDialog(self, vals)
        self.wait_window(dialog)
        if dialog.result:
            self._tree.item(item, values=dialog.result)

    def _delete_layer(self):
        sel = self._tree.selection()
        if not sel:
            return
        if messagebox.askyesno("确认", "确定删除选中的层次吗?"):
            self._tree.delete(sel[0])

    def _add_layer(self):
        dialog = LayerEditDialog(self, ["", "", "", ""])
        self.wait_window(dialog)
        if dialog.result:
            self._tree.insert("", tk.END, values=dialog.result)

    def _save_changes(self):
        """将编辑器中的层次写回选择管理器。"""
        if not self._current_method:
            return
        part, mtype, method = self._current_method

        # 收集 Treeview 中的层次数据
        new_layers = []
        children = self._tree.get_children()
        for i, item in enumerate(children):
            vals = self._tree.item(item, "values")
            new_layers.append({
                "order": i + 1,
                "material": vals[1] if len(vals) > 1 else "",
                "thickness": vals[2] if len(vals) > 2 else "",
                "note": vals[3] if len(vals) > 3 else "",
            })

        self._sel_mgr.update_method_layers(
            part, mtype, method["id"], new_layers)
        messagebox.showinfo("提示", f"构造层次已保存 ({len(new_layers)} 层)")
        if self._on_changed:
            self._on_changed()

    def clear(self):
        """清空编辑器。"""
        self._current_method = None
        self._tree.delete(*self._tree.get_children())


class LayerEditDialog(tk.Toplevel):
    """层次编辑弹出对话框。"""

    def __init__(self, parent, initial_values: list):
        super().__init__(parent)
        self.title("编辑构造层次")
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="材料及做法:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._mat_var = tk.StringVar(value=initial_values[1] if len(initial_values) > 1 else "")
        ttk.Entry(frame, textvariable=self._mat_var, width=45).grid(row=0, column=1, pady=3)

        ttk.Label(frame, text="厚度(mm):").grid(row=1, column=0, sticky=tk.W, pady=3)
        self._thk_var = tk.StringVar(value=initial_values[2] if len(initial_values) > 2 else "")
        ttk.Entry(frame, textvariable=self._thk_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=3)

        ttk.Label(frame, text="备注:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self._note_var = tk.StringVar(value=initial_values[3] if len(initial_values) > 3 else "")
        ttk.Entry(frame, textvariable=self._note_var, width=45).grid(row=2, column=1, pady=3)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def _on_ok(self):
        self.result = [
            "",  # order will be reassigned
            self._mat_var.get().strip(),
            self._thk_var.get().strip(),
            self._note_var.get().strip(),
        ]
        self.destroy()
