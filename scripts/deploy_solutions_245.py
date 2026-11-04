#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量部署Solution 2, 4, 5
"""

import json
import fc2
import zipfile
import tempfile
import shutil
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"
FUNCTION_CODE = Path(__file__).resolve().parent.parent / "function_code" / "index.py"

SOLUTIONS = {
    2: {
        'mapper_memory_mb': 192,
        'mapper_concurrency': 25,
        'reducer_memory_mb': 128,
        'num_reducers': 2,
    },
    4: {
        'mapper_memory_mb': 192,
        'mapper_concurrency': 10,
        'reducer_memory_mb': 128,
        'num_reducers': 10,
    },
    5: {
        'mapper_memory_mb': 256,
        'mapper_concurrency': 75,
        'reducer_memory_mb': 128,
        'num_reducers': 4,
    },
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
    print(f"  [部署] {function_name} ({memory_mb}MB)...", end=' ')

    temp_dir, zip_path = create_zip_package()

    try:
        try:
            client.create_function(
                serviceName=service_name,
                functionName=function_name,
                runtime='python3.9',
                handler='index.handler',
                codeZipFile=zip_path,
                memorySize=memory_mb,
                timeout=300,
                description=description
            )
            print("[OK]")
        except Exception as e:
            if 'already exists' in str(e).lower():
                client.update_function_code(
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
                print("[UPDATED]")
            else:
                raise
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def main():
    print("="*80)
    print("批量部署Solution 2, 4, 5")
    print("="*80)

    config = load_config()
    service_name = config['fc']['service_name']

    client = fc2.Client(
        endpoint=f"https://{config['account_id']}.{config['region']}.fc.aliyuncs.com",
        accessKeyID=config['access_key_id'],
        accessKeySecret=config['access_key_secret']
    )

    for sol_id, sol_config in SOLUTIONS.items():
        print(f"\nSolution {sol_id}:")
        deploy_function(
            client, service_name,
            f'solution{sol_id}-mapper',
            sol_config['mapper_memory_mb'],
            f"Solution {sol_id} Mapper"
        )
        deploy_function(
            client, service_name,
            f'solution{sol_id}-reducer',
            sol_config['reducer_memory_mb'],
            f"Solution {sol_id} Reducer"
        )

    print("\n[SUCCESS] 所有函数部署完成")

if __name__ == '__main__':
    main()
