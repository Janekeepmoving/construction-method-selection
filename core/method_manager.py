# -*- coding: utf-8 -*-
"""做法构造库管理器 —— JSON 文件读写、做法查询、增删改查、库导入导出。"""

import json
import os
import copy
from typing import Optional


class MethodLibrary:
    """做法构造库管理器。

    以部位->做法类型->做法列表 三级结构管理内置做法库。
    支持加载/保存 JSON 文件，查询/过滤做法，以及导入自定义库。
    """

    def __init__(self, library_path: str):
        self._path = library_path
        self._data: dict = {}  # {部位: {做法类型: [Method, ...]}}
        self.load()

    # ---------- 文件读写 ----------

    def load(self, path: Optional[str] = None):
        """从 JSON 文件加载做法库。"""
        p = path or self._path
        if not os.path.exists(p):
            self._data = {}
            return
        with open(p, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        if path:
            self._path = path

    def save(self, path: Optional[str] = None):
        """保存当前做法库到 JSON 文件。"""
        p = path or self._path
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def reload(self):
        """重新加载（放弃未保存修改）。"""
        self.load()

    # ---------- 查询 ----------

    def get_parts(self) -> list:
        """返回所有部位名称列表，如 ['地下室', '住宅', '公建']。"""
        return list(self._data.keys())

    def get_method_types(self, part: str) -> list:
        """返回某部位下所有做法类型名称。"""
        return list(self._data.get(part, {}).keys())

    def get_methods(self, part: str, method_type: str) -> list:
        """返回某部位-某做法类型下的全部做法列表。"""
        return self._data.get(part, {}).get(method_type, [])

    def get_method_by_id(self, method_id: str) -> Optional[dict]:
        """按编号查找做法（全库搜索）。"""
        for part_data in self._data.values():
            for methods in part_data.values():
                for m in methods:
                    if m.get("id") == method_id:
                        return m
        return None

    def search(self, keyword: str) -> list:
        """按关键词搜索做法（匹配 id/name/reference）。"""
        results = []
        for part_name, part_data in self._data.items():
            for type_name, methods in part_data.items():
                for m in methods:
                    if (keyword in m.get("id", "") or
                        keyword in m.get("name", "") or
                        keyword in m.get("reference", "")):
                        results.append((part_name, type_name, m))
        return results

    # ---------- 增删改 ----------

    def add_method(self, part: str, method_type: str, method: dict):
        """向指定部位-类型下添加一条做法。"""
        self._data.setdefault(part, {}).setdefault(method_type, []).append(method)

    def update_method(self, method_id: str, new_data: dict):
        """更新指定编号的做法（全库查找替换）。"""
        for part_data in self._data.values():
            for i, methods in enumerate(part_data.values()):
                for j, m in enumerate(methods):
                    if m.get("id") == method_id:
                        part_data[list(part_data.keys())[i]][j] = new_data
                        return True
        return False

    def delete_method(self, method_id: str):
        """删除指定编号的做法。"""
        for part_data in self._data.values():
            for type_name, methods in part_data.items():
                for i, m in enumerate(methods):
                    if m.get("id") == method_id:
                        del methods[i]
                        return True
        return False

    def add_part(self, part_name: str):
        """添加新部位分类。"""
        if part_name not in self._data:
            self._data[part_name] = {}

    def remove_part(self, part_name: str):
        """删除整个部位分类。"""
        self._data.pop(part_name, None)

    # ---------- 导入导出 ----------

    def export_to(self, path: str):
        """导出整个库到指定 JSON 文件。"""
        self.save(path)

    def import_from(self, path: str):
        """从外部 JSON 文件导入（合并模式：新增部位/做法，不删除已有）。"""
        with open(path, "r", encoding="utf-8") as f:
            ext_data = json.load(f)
        for part, part_data in ext_data.items():
            if part not in self._data:
                self._data[part] = {}
            for mtype, methods in part_data.items():
                existing = {m["id"] for m in self._data[part].get(mtype, [])}
                for m in methods:
                    if m["id"] not in existing:
                        self._data[part].setdefault(mtype, []).append(m)

    def import_replace(self, path: str):
        """从外部 JSON 文件完整替换当前库。"""
        self.load(path)

    def get_all_data(self) -> dict:
        """返回完整数据深拷贝（供外部遍历）。"""
        return copy.deepcopy(self._data)
