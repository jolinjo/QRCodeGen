#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程式測試
"""

import sys
import os

# 將 src 目錄加入路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import main

def test_main():
    """測試主函數"""
    # 這是一個簡單的測試範例
    assert callable(main), "main 應該是一個可呼叫的函數"

if __name__ == "__main__":
    test_main()
    print("測試通過！")

