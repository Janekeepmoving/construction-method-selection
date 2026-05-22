# -*- coding: utf-8 -*-
"""选择状态管理器 —— 跟踪用户选中的部位/做法类型/具体做法，支持撤销/重做。"""

from typing import Optional
import copy


class SelectionManager:
    """管理用户的多层级选择状态。

    选择按三层组织:
      部位（part）→ 做法类型（method_type）→ 做法列表（methods）

    支持:
      - 单项选择/取消
      - 构造层次编辑覆盖（局部修改不改变库）
      - 撤销 / 重做（最多 50 步历史）
    """

    def __init__(self):
        # {part: {method_type: [edited_method_dict, ...]}}
        self._selections: dict = {}
        self._history: list = [{}]       # 初始空状态
        self._history_index: int = 0     # 指向当前状态
        self._max_history = 50

    # ---------- 选择操作 ----------

    def add_selection(self, part: str, method_type: str, method: dict):
        """将一条做法加入选择集。"""
        self._selections.setdefault(part, {}).setdefault(
            method_type, []
        ).append(copy.deepcopy(method))
        self._push_history()

    def remove_selection(self, part: str, method_type: str, method_id: str):
        """从选择集中移除某条做法。"""
        methods = self._selections.get(part, {}).get(method_type, [])
        for i, m in enumerate(methods):
            if m.get("id") == method_id:
                del methods[i]
                break
        self._push_history()

    def clear_part(self, part: str):
        """清除某部位下的所有选择。"""
        self._selections.pop(part, None)
        self._push_history()

    def clear_type(self, part: str, method_type: str):
        """清除某部位+做法类型下的选择。"""
        if part in self._selections and method_type in self._selections[part]:
            del self._selections[part][method_type]
        self._push_history()

    def clear_all(self):
        """清空全部选择。"""
        self._selections.clear()
        self._push_history()

    # ---------- 编辑选中做法 ----------

    def update_method_layers(self, part: str, method_type: str,
                             method_id: str, new_layers: list):
        """更新某条已选做法的构造层次（局部修改，不影响原库）。"""
        methods = self._selections.get(part, {}).get(method_type, [])
        for m in methods:
            if m.get("id") == method_id:
                m["layers"] = new_layers
                break
        self._push_history()

    def update_method_field(self, part: str, method_type: str,
                            method_id: str, field: str, value):
        """更新已选做法的单个字段（如 name, reference 等）。"""
        methods = self._selections.get(part, {}).get(method_type, [])
        for m in methods:
            if m.get("id") == method_id:
                m[field] = value
                break
        self._push_history()

    # ---------- 查询 ----------

    def get_selected_parts(self) -> list:
        """返回所有已选部位名。"""
        return [p for p, types in self._selections.items() if types]

    def get_selected_types(self, part: str) -> list:
        """返回某部位下已选做法类型名。"""
        return [t for t, methods in self._selections.get(part, {}).items() if methods]

    def get_selected_methods(self, part: str, method_type: str) -> list:
        """返回某部位+类型下已选的做法列表。"""
        return self._selections.get(part, {}).get(method_type, [])

    def get_all_selections(self) -> dict:
        """返回全部选择深拷贝。"""
        return copy.deepcopy(self._selections)

    def is_empty(self) -> bool:
        """无任何选择时返回 True。"""
        for part_data in self._selections.values():
            for methods in part_data.values():
                if methods:
                    return False
        return True

    # ---------- 撤销/重做 ----------

    def _push_history(self):
        """在选择变更前保存当前状态到历史栈。"""
        # 丢弃当前位置之后的历史
        self._history = self._history[:self._history_index + 1]
        self._history.append(copy.deepcopy(self._selections))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._history_index = len(self._history) - 1

    def undo(self) -> bool:
        """撤销上一步选择操作，返回是否成功。"""
        if self._history_index <= 0:
            return False
        self._history_index -= 1
        self._selections = copy.deepcopy(self._history[self._history_index])
        return True

    def redo(self) -> bool:
        """重做被撤销的操作，返回是否成功。"""
        if self._history_index >= len(self._history) - 1:
            return False
        self._history_index += 1
        self._selections = copy.deepcopy(self._history[self._history_index])
        return True

    def can_undo(self) -> bool:
        return self._history_index > 0

    def can_redo(self) -> bool:
        return self._history_index < len(self._history) - 1
