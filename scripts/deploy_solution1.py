#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署并验证Pareto Solution 1
配置: Map(192MB,并发50) + Reduce(128MB,20个)
"""

import json
import fc2
import zipfile
import tempfile
import shutil
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"
FUNCTION_CODE = Path(__file__).resolve().parent.parent / "function_code" / "index.py"

SOLUTION_1 = {
    'solution_id': 1,
    'path': [0, 1, 11, 14, 19, 20, 27],
    'mapper_memory_mb': 192,
    'mapper_concurrency': 50,
    'reducer_memory_mb': 128,
    'num_reducers': 20,
    'coordinator_memory_mb': 512,
    'predicted_time_ms': 10521.96,
    'predicted_cost_yuan': 0.00028724
}

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_zip_package():
    temp_dir = tempfile.mkdtemp()
    zip_path = Path(temp_dir) / "function.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(FUNCTION_CODE, arcname='index.py')

    return temp_dir, str(zip_path)

def deploy_function(client, service_name, function_name, memory_mb, description):
    print(f"\n[部署] {function_name} ({memory_mb}MB)...")

    temp_dir, zip_path = create_zip_package()

    try:
        try:
            response = client.create_function(
                serviceName=service_name,
                functionName=function_name,
                runtime='python3.9',
                handler='index.handler',
                codeZipFile=zip_path,
                memorySize=memory_mb,
                timeout=300,
                description=description
            )
            print(f"  [OK] 创建成功")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print(f"  [INFO] 函数已存在，正在更新...")
                response = client.update_function_code(
                    serviceName=service_name,
                    functionName=function_name,
                    codeZipFile=zip_path
                )
                client.update_function(
                    serviceName=service_name,
                    functionName=function_name,
                    memorySize=memory_mb,
                    timeout=300,
                    description=description
                )
                print(f"  [OK] 更新成功")
            else:
                raise
    finally:
        shutil.rmtree(temp_dir)

def main():
    print("="*80)
    print("部署Pareto Solution 1")
    print("="*80)

    config = load_config()
    service_name = config['fc']['service_name']

    client = fc2.Client(
        endpoint=f"https://{config['account_id']}.{config['region']}.fc.aliyuncs.com",
        accessKeyID=config['access_key_id'],
        accessKeySecret=config['access_key_secret']
    )

    # 部署函数
    deploy_function(
        client, service_name,
        'solution1-mapper', SOLUTION_1['mapper_memory_mb'],
        f"Solution 1 Mapper - {SOLUTION_1['mapper_memory_mb']}MB"
    )

    deploy_function(
        client, service_name,
        'solution1-reducer', SOLUTION_1['reducer_memory_mb'],
        f"Solution 1 Reducer - {SOLUTION_1['reducer_memory_mb']}MB"
    )

    print("\n[SUCCESS] Solution 1 部署完成")
    print(f"  - solution1-mapper ({SOLUTION_1['mapper_memory_mb']}MB)")
    print(f"  - solution1-reducer ({SOLUTION_1['reducer_memory_mb']}MB)")

if __name__ == '__main__':
    main()
