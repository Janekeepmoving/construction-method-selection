# -*- coding: utf-8 -*-
"""表格构建引擎 —— 按 5 栏布局生成统一的建筑构造做法表。

5 栏对应五大做法类型: 屋面 | 外墙 | 内墙 | 地面 | 顶棚
每栏内部有 4 个子列: 编号 | 构造层次 | 使用范围 | 备注
"""


class TableBuilder:
    """根据 SelectionManager 的选择结果构建 5 栏表格。

    输出格式:
      {
        "title": "建筑构造做法表",
        "columns": [  # 5 栏
          {
            "section_title": "一、屋面做法（R）",
            "sub_columns": [{header, width}, ...],
            "methods": [{id, layers, usage, notes}, ...],
          }, ...
        ],
        "sub_columns": [{header, width}, ...],
      }
    """

    def __init__(self, table_styles: dict):
        self._styles = table_styles

    def build_method_table(self, selections: dict) -> dict:
        """构建 5 栏数据。"""
        cfg = self._styles["table_type"]
        section_labels = self._styles.get("section_labels", {})
        section_order = self._styles.get("section_order", [])
        sub_cols = cfg["sub_columns"]

        columns_data = []
        for mtype in section_order:
            label = section_labels.get(mtype, mtype)
            methods = self._collect_methods(selections, mtype)

            methods_data = []
            for m in methods:
                methods_data.append({
                    "id": m.get("id", ""),
                    "name": m.get("name", ""),
                    "layers": m.get("layers", []),
                    "usage": m.get("usage", ""),
                    "notes": m.get("notes", ""),
                })

            columns_data.append({
                "section_title": label,
                "methods": methods_data,
            })

        return {
            "title": cfg["name"],
            "columns": columns_data,
            "sub_columns": sub_cols,
        }

    def _collect_methods(self, selections: dict, mtype: str) -> list:
        """收集所有部位下指定类型的做法。"""
        result = []
        for part_data in selections.values():
            result.extend(part_data.get(mtype, []))
        return result
