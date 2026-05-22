# -*- coding: utf-8 -*-
"""
建筑做法构造选型与自动出图软件
================================
基于中南标(15ZJ001)图集，帮助建筑师快速选择建筑构造做法，
自动生成构造做法表、装修一览表，并输出为带标准图框的 DXF/PDF 图纸。

使用方法:
  1. 安装依赖: pip install -r requirements.txt
  2. 运行程序: python main.py
  3. 按界面引导完成: 部位选择 → 做法选型 → 项目信息 → 生成图纸

依赖:
  - Python 3.8+
  - ezdxf (DXF 图纸输出)
  - reportlab (PDF 图纸输出)
  - tkinter (Python 内置，无需安装)

配置文件 (config/):
  - settings.json      全局设置（字体、线宽、图幅等）
  - methods_library.json  做法构造库（可自行添加做法）
  - title_block.json   图框图块参数
  - table_styles.json  表格样式配置

输出文件在 output_files/ 目录下。
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main():
    """启动图形用户界面。"""
    # Windows 下解决高 DPI 缩放模糊问题
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
