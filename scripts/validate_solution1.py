#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Pareto Solution 1的实际性能
配置: Map(192MB,并发50) + Reduce(128MB,20个)
预测时间: 10.52秒
预测成本: 0.00028724元
"""

import json
import time
import fc2
import oss2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"

SOLUTION_1 = {
    'solution_id': 1,
    'path': [0, 1, 11, 14, 19, 20, 27],
    'mapper_memory_mb': 192,
    'mapper_concurrency': 50,
    'reducer_memory_mb': 128,
    'num_reducers': 20,
    'objects_per_reducer': 5,
    'predicted_time_ms': 10521.96,
    'predicted_time_s': 10.52,
    'predicted_cost_yuan': 0.00028724,
    'error_threshold': 0.15
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

def list_input_files(oss_bucket, prefix='input/'):
    files = []
    for obj in oss2.ObjectIteratorV2(oss_bucket, prefix=prefix):
        if obj.key.endswith('.csv'):
            files.append(obj.key)
    return sorted(files)

def invoke_mapper(fc_client, service_name, function_name, task_id, input_file):
    payload = {
        'task_type': 'map',
        'task_id': task_id,
        'input_file': input_file
    }

    start_time = time.time()
    try:
        response = fc_client.invoke_function(
            serviceName=service_name,
            functionName=function_name,
            payload=json.dumps(payload).encode('utf-8')
        )
        duration_ms = (time.time() - start_time) * 1000
        result = json.loads(response.data.decode('utf-8'))

        return {
            'task_id': task_id,
            'success': result.get('statusCode') == 200,
            'duration_ms': duration_ms,
            'records': result.get('records_processed', 0),
            'error': None
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            'task_id': task_id,
            'success': False,
            'duration_ms': duration_ms,
            'records': 0,
            'error': str(e)
        }

def invoke_reducer(fc_client, service_name, function_name, reduce_id, map_task_ids):
    payload = {
        'task_type': 'reduce',
        'reduce_id': reduce_id,
        'map_task_ids': map_task_ids
    }

    start_time = time.time()
    try:
        response = fc_client.invoke_function(
            serviceName=service_name,
            functionName=function_name,
            payload=json.dumps(payload).encode('utf-8')
        )
        duration_ms = (time.time() - start_time) * 1000
        result = json.loads(response.data.decode('utf-8'))

        return {
            'reduce_id': reduce_id,
            'success': result.get('statusCode') == 200,
            'duration_ms': duration_ms,
            'records': result.get('records_aggregated', 0),
            'error': None
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            'reduce_id': reduce_id,
            'success': False,
            'duration_ms': duration_ms,
            'records': 0,
            'error': str(e)
        }

def main():
    print("="*80)
    print("Pareto Solution 1 性能验证")
    print("="*80)
    print()

    print("Solution 1 配置:")
    print(f"  路径: {SOLUTION_1['path']}")
    print(f"  Mapper内存: {SOLUTION_1['mapper_memory_mb']} MB")
    print(f"  Mapper并发: {SOLUTION_1['mapper_concurrency']} workers")
    print(f"  Reducer内存: {SOLUTION_1['reducer_memory_mb']} MB")
    print(f"  Reducer数量: {SOLUTION_1['num_reducers']}")
    print(f"  预测时间: {SOLUTION_1['predicted_time_s']:.2f}秒")
    print(f"  预测成本: {SOLUTION_1['predicted_cost_yuan']:.8f}元")
    print()

    config = load_config()
    service_name = config['fc']['service_name']

    print("[1/5] 创建客户端...")
    fc_client, oss_bucket = create_clients(config)
    print(f"  [OK] FC和OSS客户端已连接")

    print("\n[2/5] 扫描输入文件...")
    input_files = list_input_files(oss_bucket)
    print(f"  [OK] 找到 {len(input_files)} 个输入文件")

    num_map_tasks = min(len(input_files), 100)
    map_tasks = [(f"map_{i+1:03d}", input_files[i]) for i in range(num_map_tasks)]

    # 执行Map阶段
    print(f"\n[3/5] 执行Map阶段 ({SOLUTION_1['mapper_concurrency']}并发)...")
    map_start_time = time.time()
    map_results = []

    with ThreadPoolExecutor(max_workers=SOLUTION_1['mapper_concurrency']) as executor:
        futures = {
            executor.submit(
                invoke_mapper,
                fc_client,
                service_name,
                'solution1-mapper',
                task_id,
                input_file
            ): task_id
            for task_id, input_file in map_tasks
        }

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            map_results.append(result)
            completed += 1

            if completed % 10 == 0 or completed == num_map_tasks:
                print(f"  进度: {completed}/{num_map_tasks} 完成...")

    map_duration_ms = (time.time() - map_start_time) * 1000

    map_success = sum(1 for r in map_results if r['success'])
    map_failed = num_map_tasks - map_success

    print(f"\n  [OK] Map阶段完成: {map_duration_ms:.2f} ms ({map_duration_ms/1000:.2f}秒)")
    print(f"    成功: {map_success}/{num_map_tasks}")
    print(f"    失败: {map_failed}")

    # 执行Reduce阶段
    print(f"\n[4/5] 执行Reduce阶段 ({SOLUTION_1['num_reducers']}个Reducer)...")
    successful_map_ids = [r['task_id'] for r in map_results if r['success']]

    reduce_results = []
    reduce_start_time = time.time()

    with ThreadPoolExecutor(max_workers=SOLUTION_1['num_reducers']) as executor:
        futures = []
        for i in range(SOLUTION_1['num_reducers']):
            start_idx = i * SOLUTION_1['objects_per_reducer']
            end_idx = min(start_idx + SOLUTION_1['objects_per_reducer'], len(successful_map_ids))
            reducer_map_ids = successful_map_ids[start_idx:end_idx]

            future = executor.submit(
                invoke_reducer,
                fc_client,
                service_name,
                'solution1-reducer',
                f'reduce_{i+1:02d}',
                reducer_map_ids
            )
            futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            reduce_results.append(result)
            print(f"  Reducer {result['reduce_id']} 完成: {result['duration_ms']:.2f} ms")

    reduce_duration_ms = (time.time() - reduce_start_time) * 1000
    reduce_success = sum(1 for r in reduce_results if r['success'])

    print(f"\n  [OK] Reduce阶段完成: {reduce_duration_ms:.2f} ms ({reduce_duration_ms/1000:.2f}秒)")
    print(f"    成功: {reduce_success}/{SOLUTION_1['num_reducers']}")

    total_time_ms = map_duration_ms + reduce_duration_ms

    # 验证结果
    print("\n" + "="*80)
    print("验证结果")
    print("="*80)
    print()

    print("时间对比:")
    print(f"  预测时间:    {SOLUTION_1['predicted_time_ms']:.2f} ms ({SOLUTION_1['predicted_time_s']:.2f}秒)")
    print(f"  实际执行:    {total_time_ms:.2f} ms ({total_time_ms/1000:.2f}秒)")
    print()

    time_deviation_ms = total_time_ms - SOLUTION_1['predicted_time_ms']
    time_deviation_pct = abs(time_deviation_ms / SOLUTION_1['predicted_time_ms']) * 100

    print(f"时间误差: {time_deviation_pct:.2f}%")
    time_pass = time_deviation_pct < SOLUTION_1['error_threshold'] * 100
    print(f"时间验证: {'PASS' if time_pass else 'FAIL'} (阈值: 15%)")
    print()

    # 成本计算
    PRICE_PER_INVOCATION = 0.000002
    PRICE_PER_GB_SECOND = 0.00001817

    mapper_memory_gb = SOLUTION_1['mapper_memory_mb'] / 1024
    reducer_memory_gb = SOLUTION_1['reducer_memory_mb'] / 1024

    map_cost = map_success * PRICE_PER_INVOCATION + mapper_memory_gb * (map_duration_ms/1000) * PRICE_PER_GB_SECOND
    reduce_cost = reduce_success * PRICE_PER_INVOCATION + reducer_memory_gb * (reduce_duration_ms/1000) * PRICE_PER_GB_SECOND
    actual_cost = map_cost + reduce_cost

    cost_deviation_pct = abs(actual_cost - SOLUTION_1['predicted_cost_yuan']) / SOLUTION_1['predicted_cost_yuan'] * 100
    cost_pass = cost_deviation_pct < SOLUTION_1['error_threshold'] * 100

    print(f"成本对比:")
    print(f"  预测成本: {SOLUTION_1['predicted_cost_yuan']:.8f}元")
    print(f"  实际成本: {actual_cost:.8f}元")
    print(f"成本误差: {cost_deviation_pct:.2f}%")
    print(f"成本验证: {'PASS' if cost_pass else 'FAIL'} (阈值: 15%)")
    print()

    overall_pass = time_pass and cost_pass
    accuracy = 100 - (time_deviation_pct + cost_deviation_pct) / 2

    print("="*80)
    print("Solution 1 验证结果")
    print("="*80)
    print(f"时间准确率: {100 - time_deviation_pct:.2f}%")
    print(f"成本准确率: {100 - cost_deviation_pct:.2f}%")
    print(f"总体准确率: {accuracy:.2f}%")
    print(f"验证状态: {'✅ PASS' if overall_pass else '❌ FAIL'}")
    print()

    # 保存结果
    result_file = Path("solution1_validation_result.json")
    validation_data = {
        'timestamp': datetime.now().isoformat(),
        'solution': SOLUTION_1,
        'execution': {
            'map_phase': {
                'duration_ms': map_duration_ms,
                'tasks_total': num_map_tasks,
                'tasks_success': map_success,
                'tasks_failed': map_failed,
            },
            'reduce_phase': {
                'duration_ms': reduce_duration_ms,
                'reducers_total': SOLUTION_1['num_reducers'],
                'reducers_success': reduce_success,
            },
            'total_time_ms': total_time_ms
        },
        'comparison': {
            'predicted_ms': SOLUTION_1['predicted_time_ms'],
            'actual_ms': total_time_ms,
            'time_error_pct': time_deviation_pct,
            'predicted_cost': SOLUTION_1['predicted_cost_yuan'],
            'actual_cost': actual_cost,
            'cost_error_pct': cost_deviation_pct,
            'time_pass': time_pass,
            'cost_pass': cost_pass,
            'overall_pass': overall_pass,
            'accuracy': accuracy
        }
    }

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(validation_data, f, indent=2, ensure_ascii=False)

    print(f"详细结果已保存: {result_file}")
    print("="*80)

if __name__ == '__main__':
    main()
