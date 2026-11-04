#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署Pareto Solution 3的函数到阿里云FC
配置: Map(128MB,并发100) + Reduce(128MB,4个)
"""

import json
import fc2
import zipfile
import tempfile
import shutil
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "aliyun_config.json"
FUNCTION_CODE = Path(__file__).resolve().parent.parent / "function_code" / "index.py"

# Pareto Solution 3配置
SOLUTION_3 = {
    'solution_id': 3,
    'path': [0, 1, 13, 17, 19, 20, 27],
    'mapper_memory_mb': 128,
    'mapper_concurrency': 100,
    'reducer_memory_mb': 128,
    'num_reducers': 4,
    'coordinator_memory_mb': 512,
    'predicted_time_ms': 15106.79,
    'predicted_cost_yuan': 0.00036329
}

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_zip_package():
    """创建函数代码的zip包"""
    temp_dir = tempfile.mkdtemp()
    zip_path = Path(temp_dir) / "function.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(FUNCTION_CODE, arcname='index.py')

    return temp_dir, str(zip_path)

def deploy_function(client, service_name, function_name, memory_mb, description):
    """部署或更新函数"""
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
            if 'already exists' in str(e).lower() or 'alreadyexists' in str(e).lower():
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

    except Exception as e:
        print(f"  [ERROR] 错误: {e}")
        raise
    finally:
        shutil.rmtree(temp_dir)

def main():
    print("=" * 80)
    print("部署Pareto Solution 3函数")
    print("=" * 80)
    print()

    print("Pareto Solution 3配置:")
    print(f"  路径: {SOLUTION_3['path']}")
    print(f"  Mapper内存: {SOLUTION_3['mapper_memory_mb']} MB")
    print(f"  Mapper并发: {SOLUTION_3['mapper_concurrency']}")
    print(f"  Reducer内存: {SOLUTION_3['reducer_memory_mb']} MB")
    print(f"  Reducer数量: {SOLUTION_3['num_reducers']}")
    print(f"  预测时间: {SOLUTION_3['predicted_time_ms']/1000:.2f} 秒")
    print(f"  预测成本: {SOLUTION_3['predicted_cost_yuan']:.8f} 元")
    print()

    # 加载配置
    print("[1/3] 加载配置...")
    config = load_config()
    service_name = config['fc']['service_name']
    print(f"  服务名: {service_name}")

    # 创建FC客户端
    print("\n[2/3] 创建FC客户端...")
    client = fc2.Client(
        endpoint=f"https://{config['account_id']}.{config['region']}.fc.aliyuncs.com",
        accessKeyID=config['access_key_id'],
        accessKeySecret=config['access_key_secret']
    )
    print(f"  [OK] 已连接")

    # 部署函数
    print("\n[3/3] 部署函数...")

    # Mapper (128MB)
    deploy_function(
        client, service_name,
        'solution3-mapper', SOLUTION_3['mapper_memory_mb'],
        f"Solution 3 Mapper - {SOLUTION_3['mapper_memory_mb']}MB, {SOLUTION_3['mapper_concurrency']} concurrency"
    )

    # Reducer (128MB)
    deploy_function(
        client, service_name,
        'solution3-reducer', SOLUTION_3['reducer_memory_mb'],
        f"Solution 3 Reducer - {SOLUTION_3['reducer_memory_mb']}MB, {SOLUTION_3['num_reducers']} reducers"
    )

    print("\n" + "=" * 80)
    print("[SUCCESS] 部署完成！")
    print("=" * 80)
    print("\n已部署的函数:")
    print(f"  - solution3-mapper ({SOLUTION_3['mapper_memory_mb']}MB)")
    print(f"  - solution3-reducer ({SOLUTION_3['reducer_memory_mb']}MB)")
    print("\n下一步:")
    print("  运行 validate_solution3.py 进行性能验证")

if __name__ == '__main__':
    main()
