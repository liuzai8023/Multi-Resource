#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Pareto Solution 3的实际性能
配置: Map(128MB,并发100) + Reduce(128MB,4个)
预测时间: 15.11秒
预测成本: 0.00036329元
"""

import json
import time
import fc2
import oss2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"

SOLUTION_3 = {
    'solution_id': 3,
    'path': [0, 1, 13, 17, 19, 20, 27],
    'mapper_memory_mb': 128,
    'mapper_concurrency': 100,
    'reducer_memory_mb': 128,
    'num_reducers': 4,
    'objects_per_reducer': 25,  # 100个Map输出 / 4个Reducer
    'predicted_time_ms': 15106.79,
    'predicted_time_s': 15.11,
    'predicted_cost_yuan': 0.00036329,
    'error_threshold': 0.15  # 15%
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
            'timing': result.get('timing', {}),
            'error': None
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            'task_id': task_id,
            'success': False,
            'duration_ms': duration_ms,
            'records': 0,
            'timing': {},
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
            'timing': result.get('timing', {}),
            'error': None
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            'reduce_id': reduce_id,
            'success': False,
            'duration_ms': duration_ms,
            'records': 0,
            'timing': {},
            'error': str(e)
        }

def main():
    print("=" * 80)
    print("Pareto Solution 3 性能验证")
    print("=" * 80)
    print()

    print("Solution 3 配置:")
    print(f"  路径: {SOLUTION_3['path']}")
    print(f"  Mapper内存: {SOLUTION_3['mapper_memory_mb']} MB")
    print(f"  Mapper并发: {SOLUTION_3['mapper_concurrency']} workers")
    print(f"  Reducer内存: {SOLUTION_3['reducer_memory_mb']} MB")
    print(f"  Reducer数量: {SOLUTION_3['num_reducers']}")
    print(f"  预测时间: {SOLUTION_3['predicted_time_ms']:.2f} ms ({SOLUTION_3['predicted_time_s']:.2f}秒)")
    print(f"  预测成本: {SOLUTION_3['predicted_cost_yuan']:.8f} 元")
    print()

    # 加载配置
    print("[1/5] 加载配置...")
    config = load_config()
    service_name = config['fc']['service_name']
    print(f"  [OK] 服务: {service_name}")

    # 创建客户端
    print("\n[2/5] 创建客户端...")
    fc_client, oss_bucket = create_clients(config)
    print(f"  [OK] FC和OSS客户端已连接")

    # 列出输入文件
    print("\n[3/5] 扫描输入文件...")
    input_files = list_input_files(oss_bucket)
    print(f"  [OK] 找到 {len(input_files)} 个输入文件")

    if len(input_files) == 0:
        print("  [ERROR] 没有找到输入文件！")
        return

    # 准备Map任务（最多100个）
    num_map_tasks = min(len(input_files), 100)
    map_tasks = []
    for i in range(num_map_tasks):
        task_id = f"map_{i+1:03d}"
        input_file = input_files[i]
        map_tasks.append((task_id, input_file))

    print(f"  将执行 {num_map_tasks} 个Map任务")

    # 执行Map阶段（100并发）
    print(f"\n[4/5] 执行Map阶段 ({SOLUTION_3['mapper_concurrency']}并发)...")
    map_start_time = time.time()
    map_results = []

    with ThreadPoolExecutor(max_workers=SOLUTION_3['mapper_concurrency']) as executor:
        futures = {
            executor.submit(
                invoke_mapper,
                fc_client,
                service_name,
                'solution3-mapper',
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

    # 统计Map结果
    map_success = sum(1 for r in map_results if r['success'])
    map_failed = num_map_tasks - map_success
    total_records = sum(r['records'] for r in map_results)

    print(f"\n  [OK] Map阶段完成: {map_duration_ms:.2f} ms ({map_duration_ms/1000:.2f}秒)")
    print(f"    成功: {map_success}/{num_map_tasks}")
    print(f"    失败: {map_failed}")
    print(f"    处理记录数: {total_records:,}")

    if map_failed > 0:
        print(f"\n  [WARNING] 有 {map_failed} 个Map任务失败")

    # 执行Reduce阶段（4个Reducer）
    print(f"\n[5/5] 执行Reduce阶段 ({SOLUTION_3['num_reducers']}个Reducer)...")
    successful_map_ids = [r['task_id'] for r in map_results if r['success']]

    # 将Map输出分配给4个Reducer
    reduce_results = []
    reduce_start_time = time.time()

    with ThreadPoolExecutor(max_workers=SOLUTION_3['num_reducers']) as executor:
        futures = []
        for i in range(SOLUTION_3['num_reducers']):
            # 每个Reducer处理25个Map输出
            start_idx = i * SOLUTION_3['objects_per_reducer']
            end_idx = min(start_idx + SOLUTION_3['objects_per_reducer'], len(successful_map_ids))
            reducer_map_ids = successful_map_ids[start_idx:end_idx]

            future = executor.submit(
                invoke_reducer,
                fc_client,
                service_name,
                'solution3-reducer',
                f'reduce_{i+1:02d}',
                reducer_map_ids
            )
            futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            reduce_results.append(result)
            print(f"  Reducer {result['reduce_id']} 完成: {result['duration_ms']:.2f} ms")

    reduce_duration_ms = (time.time() - reduce_start_time) * 1000

    # 统计Reduce结果
    reduce_success = sum(1 for r in reduce_results if r['success'])
    total_aggregated = sum(r['records'] for r in reduce_results)

    print(f"\n  [OK] Reduce阶段完成: {reduce_duration_ms:.2f} ms ({reduce_duration_ms/1000:.2f}秒)")
    print(f"    成功: {reduce_success}/{SOLUTION_3['num_reducers']}")
    print(f"    聚合记录数: {total_aggregated:,}")

    # 总时间
    total_time_ms = map_duration_ms + reduce_duration_ms

    # 结果对比
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)
    print()

    print("时间对比:")
    print(f"  预测时间:    {SOLUTION_3['predicted_time_ms']:.2f} ms ({SOLUTION_3['predicted_time_s']:.2f}秒)")
    print(f"  实际执行:    {total_time_ms:.2f} ms ({total_time_ms/1000:.2f}秒)")
    print(f"    - Map阶段:  {map_duration_ms:.2f} ms ({map_duration_ms/1000:.2f}秒)")
    print(f"    - Reduce阶段: {reduce_duration_ms:.2f} ms ({reduce_duration_ms/1000:.2f}秒)")
    print()

    time_deviation_ms = total_time_ms - SOLUTION_3['predicted_time_ms']
    time_deviation_pct = (time_deviation_ms / SOLUTION_3['predicted_time_ms']) * 100

    print(f"时间偏差:")
    print(f"  绝对偏差: {time_deviation_ms:+.2f} ms")
    print(f"  相对偏差: {time_deviation_pct:+.2f}%")
    print()

    # 成本（需要从账单查询）
    print("成本查询:")
    print(f"  预测成本: {SOLUTION_3['predicted_cost_yuan']:.8f} 元")
    print("  [INFO] 请从阿里云账单中心查询实际成本")
    print(f"  查询时间范围: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # 验证是否通过
    time_pass = abs(time_deviation_pct) < SOLUTION_3['error_threshold'] * 100

    print("=" * 80)
    print("验证结果总结")
    print("=" * 80)
    print()

    print(f"时间验证: {'[PASS]' if time_pass else '[FAIL]'} (阈值: {SOLUTION_3['error_threshold']*100}%)")
    print(f"  误差: {abs(time_deviation_pct):.2f}%")
    print()

    if time_pass:
        print("[SUCCESS] 时间预测通过验证！")
    else:
        print("[FAIL] 时间预测未通过验证")
        print()
        print("需要校准模型:")
        time_ratio = total_time_ms / SOLUTION_3['predicted_time_ms']
        print(f"  时间比例: {time_ratio:.4f}")
        print(f"  建议调整 BASE_PROCESSING_SPEED_KBPS: {4.6816 / time_ratio:.4f}")

    # 保存详细结果
    output_file = Path(__file__).resolve().parent.parent / "results" / "solution3_validation_result.json"

    validation_data = {
        'timestamp': datetime.now().isoformat(),
        'solution': SOLUTION_3,
        'execution': {
            'map_phase': {
                'duration_ms': map_duration_ms,
                'tasks_total': num_map_tasks,
                'tasks_success': map_success,
                'tasks_failed': map_failed,
                'records_processed': total_records
            },
            'reduce_phase': {
                'duration_ms': reduce_duration_ms,
                'reducers_total': SOLUTION_3['num_reducers'],
                'reducers_success': reduce_success,
                'records_aggregated': total_aggregated
            },
            'total_time_ms': total_time_ms
        },
        'comparison': {
            'predicted_ms': SOLUTION_3['predicted_time_ms'],
            'actual_ms': total_time_ms,
            'deviation_ms': time_deviation_ms,
            'deviation_pct': time_deviation_pct,
            'time_pass': time_pass
        },
        'map_results': map_results,
        'reduce_results': reduce_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validation_data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 80)
    print(f"[OK] 详细结果已保存到: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()
