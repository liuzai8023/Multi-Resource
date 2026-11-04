#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据Solution 3的实际测量结果自动校准模型参数
"""

import json
from pathlib import Path

# 读取验证结果
result_file = Path(__file__).resolve().parent.parent / "results" / "solution3_validation_result.json"
with open(result_file, 'r', encoding='utf-8') as f:
    validation_data = json.load(f)

print("="*80)
print("自动校准模型参数")
print("="*80)
print()

# 提取数据
predicted_time_ms = validation_data['solution']['predicted_time_ms']
actual_time_ms = validation_data['comparison']['actual_ms']
time_ratio = actual_time_ms / predicted_time_ms

print("验证结果:")
print(f"  预测时间: {predicted_time_ms:.2f} ms")
print(f"  实际时间: {actual_time_ms:.2f} ms")
print(f"  时间比例: {time_ratio:.4f}")
print(f"  偏差: {validation_data['comparison']['deviation_pct']:.2f}%")
print()

print("="*80)
print("模型参数校准")
print("="*80)
print()

# 当前模型参数
CURRENT_BASE_SPEED = 4.6816  # KB/ms
CURRENT_OVERHEAD_BASE = 0.1748
CURRENT_OVERHEAD_FACTOR = 10.9398

# 计算新参数
# 如果实际时间更短，说明处理速度更快
NEW_BASE_SPEED = CURRENT_BASE_SPEED / time_ratio

print("处理速度校准:")
print(f"  当前 BASE_PROCESSING_SPEED_KBPS = {CURRENT_BASE_SPEED:.4f}")
print(f"  建议 BASE_PROCESSING_SPEED_KBPS = {NEW_BASE_SPEED:.4f}")
print(f"  变化: {(NEW_BASE_SPEED/CURRENT_BASE_SPEED - 1)*100:+.2f}%")
print()

# 读取generate_nsga_instance.py
instance_file = Path(__file__).resolve().parent.parent / "instance" / "generate_nsga_instance.py"
with open(instance_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换参数
old_line = f"BASE_PROCESSING_SPEED_KBPS = {CURRENT_BASE_SPEED}"
new_line = f"BASE_PROCESSING_SPEED_KBPS = {NEW_BASE_SPEED:.4f}"

if old_line in content:
    new_content = content.replace(old_line, new_line)

    # 备份原文件
    backup_file = Path("generate_nsga_instance_backup.py")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[OK] 原文件已备份到: {backup_file}")

    # 写入新文件
    with open(instance_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"[OK] 参数已更新: {instance_file}")
    print()

    print("="*80)
    print("下一步:")
    print("="*80)
    print()
    print("1. 重新生成算例:")
    print("   cd 'd:\\BackLab\\D\\Lab\\Cloud\\修改稿\\Case Study'")
    print("   python generate_nsga_instance.py")
    print()
    print("2. 重新运行NSGA-II:")
    print("   cd 'd:\\BackLab\\D\\Lab\\Cloud\\修改稿\\nsga'")
    print("   mvn exec:java -Dexec.args='Cloud223N28MBReal.txt'")
    print()
    print("3. 重新验证Pareto Solution 3:")
    print("   cd 'd:\\BackLab\\D\\Lab\\Cloud\\修改稿\\Case Study'")
    print("   python validate_solution3.py")
    print()
    print("="*80)

else:
    print(f"[ERROR] 未找到参数行: {old_line}")
    print("请手动修改 generate_nsga_instance.py")
    print(f"  将 BASE_PROCESSING_SPEED_KBPS 从 {CURRENT_BASE_SPEED} 改为 {NEW_BASE_SPEED:.4f}")

print()
print("="*80)
print("校准完成")
print("="*80)
