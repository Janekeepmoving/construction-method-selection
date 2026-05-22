# -*- coding: utf-8 -*-
"""表格构建引擎 —— 根据用户选择生成三种标准表格的二维数据结构。

每种表格返回格式:
  {
    "title": "表名",
    "columns": [{"header": "列名", "width": mm}, ...],
    "rows": [[cell_str, ...], ...],
    "total_width": mm,
    "total_height_estimate": mm,
  }
"""


class TableBuilder:
    """根据 SelectionManager 的选择结果构建表格数据。

    三种表格:
      1. 构造做法表 — 按部位→做法类型汇总，列出完整构造层次
      2. 建筑装修一览表 — 按楼层/空间汇总
      3. 室内装修一览表 — 细化室内各表面
    """

    def __init__(self, table_styles: dict):
        self._styles = table_styles

    # ==================== 表1：构造做法表 ====================

    def build_method_table(self, selections: dict) -> dict:
        """根据选择生成 构造做法表。

        selections: {part: {method_type: [method_dict, ...]}}
        """
        cfg = self._styles["table_types"]["构造做法表"]
        cols = cfg["columns"]

        rows = []
        seq = 0
        for part_name in ["地下室", "住宅", "公建"]:  # 固定顺序
            if part_name not in selections:
                continue
            for mtype in ["屋面做法", "外墙做法", "室内地面做法",
                          "室内墙面做法", "室内天花做法"]:
                methods = selections.get(part_name, {}).get(mtype, [])
                if not methods:
                    continue
                # 部位 / 做法类型 分组标题行
                rows.append({
                    "type": "group_header",
                    "cells": [f"{part_name} — {mtype}"],
                    "colspan": len(cols),
                })
                for method in methods:
                    layers = method.get("layers", [])
                    if not layers:
                        seq += 1
                        rows.append({
                            "type": "data",
                            "cells": [
                                f"{seq:03d}",
                                method.get("name", ""),
                                "",
                                "",
                                "",
                                method.get("reference", ""),
                            ],
                        })
                    for i, layer in enumerate(layers):
                        seq += 1
                        rows.append({
                            "type": "data",
                            "cells": [
                                f"{seq:03d}" if i == 0 else "",
                                method.get("name", "") if i == 0 else "",
                                str(layer.get("order", i + 1)),
                                layer.get("material", ""),
                                str(layer.get("thickness", "")),
                                layer.get("note", "") if i == 0
                                else (method.get("reference", "")
                                      if i == len(layers) - 1 else ""),
                            ],
                        })

        col_widths = [c["width"] for c in cols]
        total_w = sum(col_widths)
        header_h = cfg.get("header_height", 10)
        row_h = cfg.get("row_height", 8)
        title_h = cfg.get("title_height", 15)
        total_h = title_h + header_h + len(rows) * row_h + 20

        return {
            "title": "构造做法表",
            "columns": cols,
            "rows": rows,
            "total_width": total_w,
            "total_height_estimate": total_h,
            "header_height": header_h,
            "row_height": row_h,
            "title_height": title_h,
        }

    # ==================== 表2：建筑装修一览表 ====================

    def build_decoration_summary(self, selections: dict) -> dict:
        """生成 建筑装修一览表（按部位汇总）。"""
        cfg = self._styles["table_types"]["建筑装修一览表"]
        cols = cfg["columns"]

        rows = []
        for part_name in ["地下室", "住宅", "公建"]:
            if part_name not in selections:
                continue
            # 收集该部位下的所有做法名称
            ground = self._collect_names(selections, part_name, "室内地面做法")
            wall = self._collect_names(selections, part_name, "室内墙面做法")
            ceiling = self._collect_names(selections, part_name, "室内天花做法")
            roof = self._collect_names(selections, part_name, "屋面做法")
            ext_wall = self._collect_names(selections, part_name, "外墙做法")

            if ground:
                for g in ground:
                    rows.append({"type": "data", "cells": [
                        part_name, "", g, "", "", ""
                    ]})
            if wall:
                for w in wall:
                    rows.append({"type": "data", "cells": [
                        part_name, "", "", w, "", ""
                    ]})
            if ceiling:
                for c in ceiling:
                    rows.append({"type": "data", "cells": [
                        part_name, "", "", "", c, ""
                    ]})
            if roof:
                for r in roof:
                    rows.append({"type": "data", "cells": [
                        part_name, "", "", "", "",
                        f"屋面: {r}"
                    ]})
            if ext_wall:
                for ew in ext_wall:
                    rows.append({"type": "data", "cells": [
                        part_name, "", "", "", "",
                        f"外墙: {ew}"
                    ]})

        col_widths = [c["width"] for c in cols]
        total_w = sum(col_widths)
        hh = cfg.get("header_height", 10)
        rh = cfg.get("row_height", 8)
        th = cfg.get("title_height", 15)
        return {
            "title": "建筑装修一览表",
            "columns": cols,
            "rows": rows,
            "total_width": total_w,
            "total_height_estimate": th + hh + len(rows) * rh + 20,
            "header_height": hh,
            "row_height": rh,
            "title_height": th,
        }

    # ==================== 表3：室内装修一览表 ====================

    def build_interior_decoration(self, selections: dict) -> dict:
        """生成 室内装修一览表（细化室内各表面）。"""
        cfg = self._styles["table_types"]["室内装修一览表"]
        cols = cfg["columns"]

        rows = []
        for part_name in ["地下室", "住宅", "公建"]:
            if part_name not in selections:
                continue
            ground = self._collect_names(selections, part_name, "室内地面做法")
            wall = self._collect_names(selections, part_name, "室内墙面做法")
            ceiling = self._collect_names(selections, part_name, "室内天花做法")

            # 汇总同一部位的室内三面做法
            max_len = max(len(ground), len(wall), len(ceiling))
            for i in range(max_len):
                rows.append({"type": "data", "cells": [
                    part_name,
                    f"{i + 1}",
                    "",
                    ground[i] if i < len(ground) else "",
                    wall[i] if i < len(wall) else "",
                    ceiling[i] if i < len(ceiling) else "",
                    "",
                    "",
                ]})

        col_widths = [c["width"] for c in cols]
        total_w = sum(col_widths)
        hh = cfg.get("header_height", 10)
        rh = cfg.get("row_height", 8)
        th = cfg.get("title_height", 15)
        return {
            "title": "室内装修一览表",
            "columns": cols,
            "rows": rows,
            "total_width": total_w,
            "total_height_estimate": th + hh + len(rows) * rh + 20,
            "header_height": hh,
            "row_height": rh,
            "title_height": th,
        }

    # ==================== 辅助 ====================

    @staticmethod
    def _collect_names(selections: dict, part: str, mtype: str) -> list:
        """收集某部位-类型下所有选中做法的名称。"""
        names = []
        for m in selections.get(part, {}).get(mtype, []):
            names.append(m.get("name", ""))
        return names
