# -*- coding: utf-8 -*-
"""项目管理器 —— 存储项目信息与图框内容，供表格标题栏和图框图块填充使用。"""

import json
import os
from typing import Optional


class ProjectInfo:
    """项目信息数据类。

    保存项目名称、图纸名称、图号、设计人、日期、比例等图框标题栏信息。
    支持保存/加载为 JSON 便于再次编辑。
    """

    def __init__(self):
        self.project_name: str = ""       # 项目名称
        self.drawing_name: str = ""       # 图纸名称（如"构造做法表"）
        self.drawing_number: str = ""     # 图号（如"建施-01"）
        self.designer: str = ""           # 设计人
        self.date: str = ""               # 日期
        self.scale: str = ""              # 比例
        self.drawing_type: str = ""       # 图别（如"建施"）
        self.design_number: str = ""      # 设计号
        self.reviewer: str = ""           # 审核人
        self.approver: str = ""           # 审定人

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "drawing_name": self.drawing_name,
            "drawing_number": self.drawing_number,
            "designer": self.designer,
            "date": self.date,
            "scale": self.scale,
            "drawing_type": self.drawing_type,
            "design_number": self.design_number,
            "reviewer": self.reviewer,
            "approver": self.approver,
        }

    def from_dict(self, d: dict):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.from_dict(json.load(f))
