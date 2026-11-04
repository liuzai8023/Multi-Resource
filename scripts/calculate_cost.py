#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询阿里云账单，计算Solution 3的实际成本
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# 读取验证结果
result_file = Path(__file__).resolve().parent.parent / "results" / "solution3_validation_result.json"
with open(result_file, 'r', encoding='utf-8') as f:
    validation_data = json.load(f)

# 配置
config_path = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

print("="*80)
print("Solution 3 成本计算")
print("="*80)
print()

# 从验证结果提取执行信息
execution = validation_data['execution']
map_phase = execution['map_phase']
reduce_phase = execution['reduce_phase']

print("执行统计:")
print(f"  Map阶段:")
print(f"    - 成功任务: {map_phase['tasks_success']}")
print(f"    - 总耗时: {map_phase['duration_ms']:.2f} ms")
print(f"  Reduce阶段:")
print(f"    - 成功任务: {reduce_phase['reducers_success']}")
print(f"    - 总耗时: {reduce_phase['duration_ms']:.2f} ms")
print()

# 阿里云FC计费参数（上海区域）
PRICE_PER_INVOCATION = 0.000002  # 每次调用
PRICE_PER_GB_SECOND = 0.00003367  # 每GB·秒

# 配置
MAPPER_MEMORY_GB = 128 / 1024
REDUCER_MEMORY_GB = 128 / 1024

print("="*80)
print("成本计算（基于阿里云FC官方定价）")
print("="*80)
print()

# 1. Map阶段成本
map_invocation_cost = map_phase['tasks_success'] * PRICE_PER_INVOCATION
map_execution_cost = MAPPER_MEMORY_GB * (map_phase['duration_ms'] / 1000) * PRICE_PER_GB_SECOND
map_total_cost = map_invocation_cost + map_execution_cost

print("Map阶段成本:")
print(f"  调用费用: {map_invocation_cost:.8f} 元 ({map_phase['tasks_success']}次 × {PRICE_PER_INVOCATION}元)")
print(f"  执行费用: {map_execution_cost:.8f} 元 ({MAPPER_MEMORY_GB:.4f}GB × {map_phase['duration_ms']/1000:.2f}秒 × {PRICE_PER_GB_SECOND}元)")
print(f"  小计: {map_total_cost:.8f} 元")
print()

# 2. Reduce阶段成本
reduce_invocation_cost = reduce_phase['reducers_success'] * PRICE_PER_INVOCATION
reduce_execution_cost = REDUCER_MEMORY_GB * (reduce_phase['duration_ms'] / 1000) * PRICE_PER_GB_SECOND
reduce_total_cost = reduce_invocation_cost + reduce_execution_cost

print("Reduce阶段成本:")
print(f"  调用费用: {reduce_invocation_cost:.8f} 元 ({reduce_phase['reducers_success']}次 × {PRICE_PER_INVOCATION}元)")
print(f"  执行费用: {reduce_execution_cost:.8f} 元 ({REDUCER_MEMORY_GB:.4f}GB × {reduce_phase['duration_ms']/1000:.2f}秒 × {PRICE_PER_GB_SECOND}元)")
print(f"  小计: {reduce_total_cost:.8f} 元")
print()

# 3. 总成本
total_calculated_cost = map_total_cost + reduce_total_cost

print("="*80)
print("总成本汇总")
print("="*80)
print()
print(f"计算总成本: {total_calculated_cost:.8f} 元")
print()

# 4. 与预测对比
predicted_cost = validation_data['solution']['predicted_cost_yuan']
cost_error = abs(total_calculated_cost - predicted_cost) / predicted_cost * 100

print("成本验证:")
print(f"  NSGA-II预测: {predicted_cost:.8f} 元")
print(f"  实际计算: {total_calculated_cost:.8f} 元")
print(f"  误差: {cost_error:.2f}%")
print(f"  状态: {'PASS' if cost_error < 15 else 'FAIL'} (阈值: 15%)")
print()

# 5. 保存结果
validation_data['cost_calculation'] = {
    'map_phase': {
        'invocation_cost_yuan': map_invocation_cost,
        'execution_cost_yuan': map_execution_cost,
        'total_cost_yuan': map_total_cost
    },
    'reduce_phase': {
        'invocation_cost_yuan': reduce_invocation_cost,
        'execution_cost_yuan': reduce_execution_cost,
        'total_cost_yuan': reduce_total_cost
    },
    'total_calculated_cost_yuan': total_calculated_cost,
    'predicted_cost_yuan': predicted_cost,
    'cost_error_percent': cost_error,
    'cost_pass': cost_error < 15
}

with open(result_file, 'w', encoding='utf-8') as f:
    json.dump(validation_data, f, indent=2, ensure_ascii=False)

print(f"[OK] 结果已保存到: {result_file}")
print()

# 6. 最终验证结果
print("="*80)
print("最终验证结果")
print("="*80)
print()

time_pass = validation_data['comparison']['time_pass']
cost_pass = cost_error < 15

print("| 指标 | NSGA-II预测 | 实际测量 | 误差 | 是否合格 |")
print("|" + "-"*78 + "|")
print(f"| 时间 | {validation_data['solution']['predicted_time_s']:.2f}秒 | "
      f"{validation_data['comparison']['actual_ms']/1000:.2f}秒 | "
      f"{abs(validation_data['comparison']['deviation_pct']):.2f}% | "
      f"{'PASS' if time_pass else 'FAIL'} |")
print(f"| 成本 | {predicted_cost:.8f}元 | "
      f"{total_calculated_cost:.8f}元 | "
      f"{cost_error:.2f}% | "
      f"{'PASS' if cost_pass else 'FAIL'} |")
print("="*80)
print()

if time_pass and cost_pass:
    print("[SUCCESS] 验证完全通过！时间和成本预测均准确！")
    print()
    print("Pareto Solution 3 已通过完整验证，可用于论文！")
else:
    if not cost_pass:
        print("[WARNING] 成本误差超过15%，需要校准成本参数")
        print()
        print(f"建议调整:")
        cost_ratio = total_calculated_cost / predicted_cost
        print(f"  PRICE_PER_GB_SECOND: {PRICE_PER_GB_SECOND} -> {PRICE_PER_GB_SECOND * cost_ratio:.8f}")

print()
print("="*80)
print("成本计算完成")
print("="*80)
