# -*- coding: utf-8 -*-
"""主窗口 —— 引导式操作流程：部位选择 → 做法选型 → 项目信息 → 生成图纸。"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json

from .method_selector import MethodSelector
from .layer_editor import LayerEditor
from .preview_panel import PreviewPanel
from .project_dialog import ProjectDialog

from core.method_manager import MethodLibrary
from core.project_manager import ProjectInfo
from core.selection_manager import SelectionManager
from core.table_builder import TableBuilder
from output.dxf_exporter import DXFExporter
from output.pdf_exporter import PDFExporter


class MainWindow(tk.Tk):
    """应用程序主窗口。

    布局:
      - 顶部: 工具栏（项目信息、图幅/格式选择、生成按钮）
      - 左侧: 做法选择面板
      - 中间: 构造层次编辑
      - 右侧: 表格预览
      - 底部: 状态栏
    """

    def __init__(self):
        super().__init__()

        # ---- 加载配置 ----
        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._config_dir = os.path.join(self._base_dir, "config")
        self._output_dir = os.path.join(self._base_dir, "output_files")

        # 全局设置
        with open(os.path.join(self._config_dir, "settings.json"),
                  "r", encoding="utf-8") as f:
            self._settings = json.load(f)

        # 表格样式
        with open(os.path.join(self._config_dir, "table_styles.json"),
                  "r", encoding="utf-8") as f:
            self._table_styles = json.load(f)


        # ---- 核心模块 ----
        lib_path = os.path.join(self._config_dir, "methods_library.json")
        self._library = MethodLibrary(lib_path)
        self._project = ProjectInfo()
        self._selection = SelectionManager()
        self._table_builder = TableBuilder(self._table_styles)

        # ---- UI 构建 ----
        self.title("建筑做法构造选型与自动出图软件")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        # ---- 快捷键 ----
        self.bind_all("<Control-z>", lambda e: self._selection.undo() or
                      self._refresh_all())
        self.bind_all("<Control-y>", lambda e: self._selection.redo() or
                      self._refresh_all())
        self.bind_all("<Control-s>", lambda e: self._on_generate())

        # ---- 启动初始状态 ----
        self._refresh_all()

        # 居中窗口
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - 1100) // 2}+{(sh - 720) // 2}")

    # ================ 顶部工具栏 ================

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=5)
        bar.pack(fill=tk.X, side=tk.TOP)

        # 项目信息按钮
        ttk.Button(bar, text="项目信息设置",
                   command=self._on_project_info).pack(side=tk.LEFT, padx=3)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # 图幅选择
        ttk.Label(bar, text="图幅:").pack(side=tk.LEFT)
        self._paper_var = tk.StringVar(value="custom_736x574")
        paper_combo = ttk.Combobox(bar, textvariable=self._paper_var,
                                    values=["custom_736x574"], state="readonly",
                                    width=14)
        paper_combo.pack(side=tk.LEFT, padx=2)

        # 格式选择
        ttk.Label(bar, text="格式:").pack(side=tk.LEFT, padx=(8, 0))
        self._fmt_var = tk.StringVar(value="dxf")
        fmt_combo = ttk.Combobox(bar, textvariable=self._fmt_var,
                                  values=["dxf", "pdf"], state="readonly",
                                  width=5)
        fmt_combo.pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # 输出目录
        ttk.Label(bar, text="输出:").pack(side=tk.LEFT)
        self._out_dir_var = tk.StringVar(value=self._output_dir)
        out_entry = ttk.Entry(bar, textvariable=self._out_dir_var, width=20)
        out_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="浏览...",
                   command=self._on_browse_output).pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # 生成按钮
        self._gen_btn = ttk.Button(bar, text="一键生成图纸",
                                    command=self._on_generate)
        self._gen_btn.pack(side=tk.LEFT, padx=5)

        # 右侧: 库管理菜单
        ttk.Button(bar, text="导入做法库...",
                   command=self._on_import_library).pack(side=tk.RIGHT, padx=3)
        ttk.Button(bar, text="保存做法库...",
                   command=self._on_save_library).pack(side=tk.RIGHT, padx=3)

    # ================ 主区域 ================

    def _build_main_area(self):
        """三栏布局：选择 | 编辑 | 预览。"""
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # 左侧: 做法选择器
        self._selector = MethodSelector(
            main, self._library, self._selection,
            on_selection_changed=self._on_selection_changed)
        self._selector.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 中间: 层次编辑器
        self._layer_editor = LayerEditor(
            main, self._selection, on_changed=self._on_selection_changed)
        self._layer_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 右侧: 预览面板
        self._preview = PreviewPanel(main)
        self._preview.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 绑定选中做法到层次编辑器
        self._selector._selected_tree.bind(
            "<<TreeviewSelect>>", self._on_tree_select)

    # ================ 状态栏 ================

    def _build_statusbar(self):
        self._status = ttk.Label(self, text="就绪 - 请选择建筑部位和做法",
                                  relief=tk.SUNKEN, anchor=tk.W, padding=3)
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

    def _set_status(self, msg: str):
        self._status.config(text=msg)

    # ================ 事件处理 ================

    def _on_project_info(self):
        """打开项目信息对话框。"""
        ProjectDialog(self, self._project)
        # 更新状态
        if self._project.project_name:
            self._set_status(f"项目: {self._project.project_name} | "
                             f"图纸: {self._project.drawing_name or '未设定'}")

    def _on_browse_output(self):
        """选择输出目录。"""
        d = filedialog.askdirectory(initialdir=self._output_dir)
        if d:
            self._out_dir_var.set(d)

    def _on_selection_changed(self):
        """选择变更时刷新预览。"""
        self._refresh_all()

    def _on_tree_select(self, event=None):
        """右侧已选树选中项变更时，加载到层次编辑器。"""
        detail = self._selector.get_selected_method_detail()
        if detail:
            part, mtype, method = detail
            self._layer_editor.load_method(part, mtype, method)
            self._set_status(f"正在编辑: [{method['id']}] {method['name']} "
                             f"({len(method.get('layers', []))} 层)")
        else:
            self._layer_editor.clear()

    def _refresh_all(self):
        """刷新预览面板和状态栏。"""
        selections = self._selection.get_all_selections()
        self._preview.update_preview(self._table_builder, selections)

        # 统计
        total_methods = sum(
            len(methods)
            for part_data in selections.values()
            for methods in part_data.values()
        )
        total_layers = sum(
            len(m.get("layers", []))
            for part_data in selections.values()
            for methods in part_data.values()
            for m in methods
        )
        self._set_status(
            f"已选: {total_methods} 条做法, {total_layers} 构造层 | "
            f"图幅: 736×574mm | "
            f"格式: {self._fmt_var.get().upper()} | "
            f"输出: {self._out_dir_var.get()}"
        )

    # ================ 生成图纸 ================

    def _on_generate(self):
        """一键生成建筑构造做法表图纸。"""
        selections = self._selection.get_all_selections()
        if self._selection.is_empty():
            messagebox.showwarning("提示", "请先选择至少一条做法")
            return

        if not self._project.project_name:
            messagebox.showinfo("提示", "请先设置项目信息")
            self._on_project_info()
            if not self._project.project_name:
                return

        fmt = self._fmt_var.get()
        out_dir = self._out_dir_var.get()
        os.makedirs(out_dir, exist_ok=True)

        # 生成统一的构造做法表
        table_data = self._table_builder.build_method_table(selections)

        fname = f"{self._project.project_name}_构造做法表"

        try:
            if fmt == "dxf":
                exporter = DXFExporter(self._settings, self._table_styles)
                out_path = os.path.join(out_dir, f"{fname}.dxf")
                result = exporter.export(table_data, self._project, out_path)
            else:
                exporter = PDFExporter(self._settings, self._table_styles)
                out_path = os.path.join(out_dir, f"{fname}.pdf")
                result = exporter.export(table_data, self._project, out_path)

            self._set_status(f"生成完成! {result}")
            messagebox.showinfo(
                "生成成功",
                f"已生成图纸:\n\n  • {result}\n\n保存在: {out_dir}"
            )

        except Exception as e:
            messagebox.showerror("生成失败", f"出错了:\n{str(e)}")
            self._set_status(f"错误: {str(e)}")

    # ================ 做法库管理 ================

    def _on_import_library(self):
        """导入外部做法库 JSON。"""
        path = filedialog.askopenfilename(
            title="导入做法库",
            filetypes=[("JSON 文件", "*.json"), ("全部文件", "*.*")],
            initialdir=self._config_dir)
        if not path:
            return
        try:
            self._library.import_from(path)
            self._library.save()
            # 重建选择器
            self._selector.destroy()
            self._selector = MethodSelector(
                self, self._library, self._selection,
                on_selection_changed=self._on_selection_changed)
            # 注意: 简化处理，实际应刷新部件
            messagebox.showinfo("成功", "做法库已合并导入")
            self._set_status("做法库已更新")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def _on_save_library(self):
        """另存做法库。"""
        path = filedialog.asksaveasfilename(
            title="保存做法库",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")],
            initialdir=self._config_dir)
        if not path:
            return
        try:
            self._library.save(path)
            messagebox.showinfo("成功", f"做法库已保存到:\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
