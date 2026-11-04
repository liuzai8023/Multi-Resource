#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校准成本参数
"""

import json
from pathlib import Path

# 读取成本计算结果
result_file = Path(__file__).resolve().parent.parent / "results" / "solution3_validation_result.json"
with open(result_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

predicted_cost = data['solution']['predicted_cost_yuan']
actual_cost = data['cost_calculation']['total_calculated_cost_yuan']
cost_ratio = actual_cost / predicted_cost

print("="*80)
print("成本参数校准")
print("="*80)
print()

print("成本验证:")
print(f"  预测成本: {predicted_cost:.8f} 元")
print(f"  实际成本: {actual_cost:.8f} 元")
print(f"  成本比例: {cost_ratio:.4f}")
print(f"  误差: {abs(1-cost_ratio)*100:.2f}%")
print()

# 当前参数
CURRENT_PRICE_PER_GB_SECOND = 0.00003367
CURRENT_PRICE_PER_INVOCATION = 0.000002

# 计算新参数（成本比实际低，说明单价被高估了）
NEW_PRICE_PER_GB_SECOND = CURRENT_PRICE_PER_GB_SECOND * cost_ratio

print("校准参数:")
print(f"  当前 PRICE_PER_GB_SECOND = {CURRENT_PRICE_PER_GB_SECOND:.8f}")
print(f"  建议 PRICE_PER_GB_SECOND = {NEW_PRICE_PER_GB_SECOND:.8f}")
print(f"  变化: {(NEW_PRICE_PER_GB_SECOND/CURRENT_PRICE_PER_GB_SECOND - 1)*100:+.2f}%")
print()

# 读取generate_nsga_instance.py
instance_file = Path(__file__).resolve().parent.parent / "instance" / "generate_nsga_instance.py"
with open(instance_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换成本参数
old_line = f"PRICE_PER_GB_SECOND = {CURRENT_PRICE_PER_GB_SECOND}"
new_line = f"PRICE_PER_GB_SECOND = {NEW_PRICE_PER_GB_SECOND:.8f}"

if old_line in content:
    new_content = content.replace(old_line, new_line)

    # 写入新文件
    with open(instance_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"[OK] 参数已更新: {instance_file}")
    print()

    print("="*80)
    print("下一步: 重新运行完整验证流程")
    print("="*80)
    print()
    print("1. 重新生成算例:")
    print("   python generate_nsga_instance.py")
    print()
    print("2. 重新运行NSGA-II:")
    print("   cd ../nsga")
    print("   mvn -q exec:java -Dexec.mainClass='com.nsga2.scheduler.SingleInstanceRunner' -Dexec.args='Cloud223N28MBReal.txt'")
    print()
    print("3. 重新验证:")
    print("   cd '../Case Study'")
    print("   python validate_solution3.py")
    print("   python calculate_cost.py")
    print()

else:
    print(f"[ERROR] 未找到参数行")
    print("请手动修改")

print("="*80)
