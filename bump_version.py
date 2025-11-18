#!/usr/bin/env python3
"""自動累進版本號的腳本"""
import re
import sys


def read_version():
    """讀取當前版本號"""
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("錯誤：找不到 VERSION 檔案", file=sys.stderr)
        sys.exit(1)


def write_version(version):
    """寫入版本號"""
    with open('VERSION', 'w') as f:
        f.write(version + '\n')


def bump_version(current_version, bump_type='patch'):
    """
    累進版本號
    
    Args:
        current_version: 當前版本號（例如 '1.0.0'）
        bump_type: 累進類型 - 'major', 'minor', 或 'patch'
    
    Returns:
        新的版本號
    """
    # 解析版本號
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', current_version)
    if not match:
        print(f"錯誤：無效的版本號格式：{current_version}", file=sys.stderr)
        sys.exit(1)
    
    major, minor, patch = map(int, match.groups())
    
    # 根據類型累進
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    return f"{major}.{minor}.{patch}"


def main():
    if len(sys.argv) > 1:
        bump_type = sys.argv[1]
        if bump_type not in ('major', 'minor', 'patch'):
            print("用法: python bump_version.py [major|minor|patch]", file=sys.stderr)
            print("預設為 patch", file=sys.stderr)
            sys.exit(1)
    else:
        bump_type = 'patch'
    
    current_version = read_version()
    new_version = bump_version(current_version, bump_type)
    write_version(new_version)
    
    print(f"版本號已更新：{current_version} -> {new_version}")
    return new_version


if __name__ == '__main__':
    main()

