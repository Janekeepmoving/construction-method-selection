# -*- coding: utf-8 -*-
"""表格构建引擎 —— 按做法类型生成统一的建筑构造做法表。

10 个做法类型按顺序排列，导出时由输出模块负责流式分栏分页。
"""


class TableBuilder:
    """根据 SelectionManager 的选择结果构建表格数据。

    输出格式:
      {
        "title": "建筑构造做法表",
        "sections": [  # 按 section_order 排列
          {"section_title": "一 屋面做法(R)", "methods": [...]},
          ...
        ],
        "sub_columns": [{header, width}, ...],
      }
    """

    def __init__(self, table_styles: dict):
        self._styles = table_styles

    def build_method_table(self, selections: dict) -> dict:
        cfg = self._styles["table_type"]
        section_labels = self._styles.get("section_labels", {})
        section_order = self._styles.get("section_order", [])
        sub_cols = cfg["sub_columns"]

        sections = []
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

            sections.append({
                "section_title": label,
                "methods": methods_data,
            })

        return {
            "title": cfg["name"],
            "sections": sections,
            "sub_columns": sub_cols,
        }

    def _collect_methods(self, selections: dict, mtype: str) -> list:
        result = []
        for part_data in selections.values():
            result.extend(part_data.get(mtype, []))
        return result
