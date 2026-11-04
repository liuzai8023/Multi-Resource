#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证Solution 2, 4, 5
"""

import json
import time
import fc2
import oss2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"

SOLUTIONS = {
    2: {
        'mapper_memory_mb': 192,
        'mapper_concurrency': 25,
        'reducer_memory_mb': 128,
        'num_reducers': 2,
        'objects_per_reducer': 50,
        'predicted_time_ms': 11407.76,
        'predicted_cost_yuan': 0.00026224,
    },
    4: {
        'mapper_memory_mb': 192,
        'mapper_concurrency': 10,
        'reducer_memory_mb': 128,
        'num_reducers': 10,
        'objects_per_reducer': 10,
        'predicted_time_ms': 14065.14,
        'predicted_cost_yuan': 0.00024724,
    },
    5: {
        'mapper_memory_mb': 256,
        'mapper_concurrency': 75,
        'reducer_memory_mb': 128,
        'num_reducers': 4,
        'objects_per_reducer': 25,
        'predicted_time_ms': 10226.70,
        'predicted_cost_yuan': 0.00031224,
    },
}

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_clients(config):
    fc_client = fc2.Client(
        endpoint=f"https://{config['account_id']}.{config['region']}.fc.aliyuncs.com",
        accessKeyID=config['access_key_id'],
        accessKeySecret=config['access_key_secret']
    )

    auth = oss2.Auth(config['access_key_id'], config['access_key_secret'])
    oss_bucket = oss2.Bucket(auth, config['oss']['endpoint'], config['oss']['bucket_name'])

    return fc_client, oss_bucket

def list_input_files(oss_bucket):
    files = []
    for obj in oss2.ObjectIteratorV2(oss_bucket, prefix='input/'):
        if obj.key.endswith('.csv'):
            files.append(obj.key)
    return sorted(files)

def invoke_mapper(fc_client, service_name, function_name, task_id, input_file):
    payload = {'task_type': 'map', 'task_id': task_id, 'input_file': input_file}
    start_time = time.time()
    try:
        response = fc_client.invoke_function(
            serviceName=service_name,
            functionName=function_name,
            payload=json.dumps(payload).encode('utf-8')
        )
        result = json.loads(response.data.decode('utf-8'))
        return {
            'task_id': task_id,
            'success': result.get('statusCode') == 200,
            'duration_ms': (time.time() - start_time) * 1000,
        }
    except:
        return {'task_id': task_id, 'success': False, 'duration_ms': (time.time() - start_time) * 1000}

def invoke_reducer(fc_client, service_name, function_name, reduce_id, map_task_ids):
    payload = {'task_type': 'reduce', 'reduce_id': reduce_id, 'map_task_ids': map_task_ids}
    start_time = time.time()
    try:
        response = fc_client.invoke_function(
            serviceName=service_name,
            functionName=function_name,
            payload=json.dumps(payload).encode('utf-8')
        )
        result = json.loads(response.data.decode('utf-8'))
        return {
            'reduce_id': reduce_id,
            'success': result.get('statusCode') == 200,
            'duration_ms': (time.time() - start_time) * 1000,
        }
    except:
        return {'reduce_id': reduce_id, 'success': False, 'duration_ms': (time.time() - start_time) * 1000}

def validate_solution(sol_id, sol_config, fc_client, oss_bucket, service_name, input_files):
    print(f"\n{'='*80}")
    print(f"验证Solution {sol_id}")
    print(f"{'='*80}")
    print(f"配置: {sol_config['mapper_memory_mb']}MB, 并发{sol_config['mapper_concurrency']}")
    print(f"预测: {sol_config['predicted_time_ms']/1000:.2f}秒, {sol_config['predicted_cost_yuan']:.8f}元")

    num_map_tasks = min(len(input_files), 100)
    map_tasks = [(f"map_{i+1:03d}", input_files[i]) for i in range(num_map_tasks)]

    # Map阶段
    print(f"\nMap阶段 ({sol_config['mapper_concurrency']}并发)...")
    map_start = time.time()
    map_results = []

    with ThreadPoolExecutor(max_workers=sol_config['mapper_concurrency']) as executor:
        futures = {
            executor.submit(invoke_mapper, fc_client, service_name, f'solution{sol_id}-mapper', tid, ifile): tid
            for tid, ifile in map_tasks
        }
        for future in as_completed(futures):
            map_results.append(future.result())

    map_duration_ms = (time.time() - map_start) * 1000
    map_success = sum(1 for r in map_results if r['success'])
    print(f"  完成: {map_duration_ms/1000:.2f}秒, 成功{map_success}/{num_map_tasks}")

    # Reduce阶段
    print(f"Reduce阶段 ({sol_config['num_reducers']}个)...")
    successful_map_ids = [r['task_id'] for r in map_results if r['success']]

    reduce_start = time.time()
    reduce_results = []

    with ThreadPoolExecutor(max_workers=sol_config['num_reducers']) as executor:
        futures = []
        for i in range(sol_config['num_reducers']):
            start_idx = i * sol_config['objects_per_reducer']
            end_idx = min(start_idx + sol_config['objects_per_reducer'], len(successful_map_ids))
            reducer_map_ids = successful_map_ids[start_idx:end_idx]

            future = executor.submit(invoke_reducer, fc_client, service_name, f'solution{sol_id}-reducer', f'r{i+1}', reducer_map_ids)
            futures.append(future)

        for future in as_completed(futures):
            reduce_results.append(future.result())

    reduce_duration_ms = (time.time() - reduce_start) * 1000
    reduce_success = sum(1 for r in reduce_results if r['success'])
    print(f"  完成: {reduce_duration_ms/1000:.2f}秒, 成功{reduce_success}/{sol_config['num_reducers']}")

    total_time_ms = map_duration_ms + reduce_duration_ms

    # 成本计算
    PRICE_PER_INVOCATION = 0.000002
    PRICE_PER_GB_SECOND = 0.00001817

    mapper_gb = sol_config['mapper_memory_mb'] / 1024
    reducer_gb = sol_config['reducer_memory_mb'] / 1024

    map_cost = map_success * PRICE_PER_INVOCATION + mapper_gb * (map_duration_ms/1000) * PRICE_PER_GB_SECOND
    reduce_cost = reduce_success * PRICE_PER_INVOCATION + reducer_gb * (reduce_duration_ms/1000) * PRICE_PER_GB_SECOND
    actual_cost = map_cost + reduce_cost

    # 计算准确率
    time_error = abs(total_time_ms - sol_config['predicted_time_ms']) / sol_config['predicted_time_ms'] * 100
    cost_error = abs(actual_cost - sol_config['predicted_cost_yuan']) / sol_config['predicted_cost_yuan'] * 100

    time_acc = 100 - time_error
    cost_acc = 100 - cost_error
    overall_acc = (time_acc + cost_acc) / 2

    print(f"\n结果:")
    print(f"  时间: 实际{total_time_ms/1000:.2f}秒, 误差{time_error:.2f}%, 准确率{time_acc:.2f}%")
    print(f"  成本: 实际{actual_cost:.8f}元, 误差{cost_error:.2f}%, 准确率{cost_acc:.2f}%")
    print(f"  总体准确率: {overall_acc:.2f}%")
    print(f"  状态: {'PASS' if (time_error < 15 and cost_error < 15) else 'FAIL'}")

    return {
        'solution_id': sol_id,
        'time_accuracy': time_acc,
        'cost_accuracy': cost_acc,
        'overall_accuracy': overall_acc,
        'time_error': time_error,
        'cost_error': cost_error,
        'actual_time_s': total_time_ms / 1000,
        'actual_cost': actual_cost,
        'map_success': map_success,
        'reduce_success': reduce_success,
    }

def main():
    print("="*80)
    print("批量验证Solution 2, 4, 5")
    print("="*80)

    config = load_config()
    service_name = config['fc']['service_name']
    fc_client, oss_bucket = create_clients(config)
    input_files = list_input_files(oss_bucket)

    results = {}
    for sol_id in [2, 4, 5]:
        results[sol_id] = validate_solution(sol_id, SOLUTIONS[sol_id], fc_client, oss_bucket, service_name, input_files)

    # 汇总
    print(f"\n{'='*80}")
    print("验证结果汇总")
    print(f"{'='*80}")

    for sol_id, result in results.items():
        print(f"Solution {sol_id}: 准确率{result['overall_accuracy']:.2f}% (时间{result['time_accuracy']:.2f}%, 成本{result['cost_accuracy']:.2f}%)")

    avg_acc = sum(r['overall_accuracy'] for r in results.values()) / len(results)
    print(f"\n平均准确率: {avg_acc:.2f}%")

    # 保存
    with open('solutions_245_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n结果已保存: solutions_245_results.json")

if __name__ == '__main__':
    main()
