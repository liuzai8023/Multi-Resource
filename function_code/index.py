# -*- coding: utf-8 -*-
"""
Universal Worker - Updated with Taobao Traffic Analysis Support

Supports multiple data types:
- 'log': Log analysis (original)
- 'taobao': Taobao user behavior traffic analysis
"""
import json
import time
import os
import oss2
from collections import defaultdict
from datetime import datetime

def handler(event, context):
    """
    Universal function: can execute Map, Reduce, and Final Reduce tasks
    Decides task type based on input parameters
    """
    start_time = time.time()

    # Parse event
    if isinstance(event, bytes):
        event = json.loads(event.decode('utf-8'))

    # Get data type (default to 'log' for backward compatibility)
    data_type = event.get('data_type', 'log')

    # Get task type
    task_type = event.get('task_type', 'map')

    # Route to appropriate handler based on data_type
    if data_type == 'taobao':
        if task_type == 'map':
            return execute_map_taobao(event, context, start_time)
        elif task_type == 'reduce':
            return execute_reduce_taobao(event, context, start_time)
        elif task_type == 'final':
            return execute_final_reduce_taobao(event, context, start_time)
    else:  # Default: log analysis
        if task_type == 'map':
            return execute_map(event, context, start_time)
        elif task_type == 'reduce':
            return execute_reduce(event, context, start_time)
        elif task_type == 'final':
            return execute_final_reduce(event, context, start_time)

    return {
        'statusCode': 400,
        'error': f'Unknown task_type: {task_type} or data_type: {data_type}'
    }

# ========== Taobao Traffic Analysis Handlers ==========

def execute_map_taobao(event, context, start_time):
    """Map Task for Taobao: Extract hourly traffic statistics"""
    task_id = event.get('task_id', 'unknown')
    input_file = event.get('input_file')

    if not input_file:
        return {'statusCode': 400, 'error': 'Missing input_file parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read CSV from OSS
    read_start = time.time()
    try:
        obj = bucket.get_object(input_file)
        csv_content = obj.read().decode('utf-8')
        input_size_bytes = len(csv_content.encode('utf-8'))
        read_time = time.time() - read_start
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to read from OSS: {str(e)}'}

    # Process CSV - extract hourly traffic
    process_start = time.time()
    lines = csv_content.strip().split('\n')

    # Initialize hourly statistics
    hourly_stats = {}
    for hour in range(24):
        hourly_stats[f"{hour:02d}"] = {
            'pv': 0,
            'users': set(),
            'buy': 0
        }

    total_records = 0

    # Parse CSV (format: user_id,item_id,category_id,behavior,timestamp)
    for line in lines:
        if not line.strip():
            continue

        parts = line.split(',')
        if len(parts) >= 5:
            total_records += 1

            try:
                user_id = parts[0].strip()
                behavior = parts[3].strip()
                timestamp = int(parts[4].strip())

                # Extract hour from timestamp
                dt = datetime.fromtimestamp(timestamp)
                hour = f"{dt.hour:02d}"

                # Count PV (all behaviors)
                hourly_stats[hour]['pv'] += 1

                # Track unique users
                hourly_stats[hour]['users'].add(user_id)

                # Count purchases
                if behavior == 'buy':
                    hourly_stats[hour]['buy'] += 1

            except (ValueError, IndexError):
                pass

    process_time = time.time() - process_start

    # Prepare output JSON (convert sets to counts)
    output_data = {
        'task_id': task_id,
        'input_file': input_file,
        'input_size_kb': round(input_size_bytes / 1024, 2),
        'total_records': total_records,
        'hourly_stats': {}
    }

    for hour, stats in hourly_stats.items():
        output_data['hourly_stats'][hour] = {
            'pv': stats['pv'],
            'unique_users': len(stats['users']),
            'buy': stats['buy']
        }

    # Write output to OSS
    write_start = time.time()
    output_key = f"map_output_taobao/{task_id}.json"
    try:
        bucket.put_object(output_key, json.dumps(output_data, ensure_ascii=False))
        write_time = time.time() - write_start
        output_size_bytes = len(json.dumps(output_data).encode('utf-8'))
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'map',
        'task_id': task_id,
        'output_file': output_key,
        'output_size_kb': round(output_size_bytes / 1024, 2),
        'records_processed': total_records,
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'process': round(process_time, 4),
            'oss_write': round(write_time, 4)
        }
    }

def execute_reduce_taobao(event, context, start_time):
    """Reduce Task for Taobao: Aggregate hourly statistics from multiple Maps"""
    reduce_id = event.get('reduce_id', 'unknown')
    map_task_ids = event.get('map_task_ids', [])

    if not map_task_ids:
        return {'statusCode': 400, 'error': 'Missing map_task_ids parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read Map outputs from OSS
    read_start = time.time()
    map_results = []
    total_input_size = 0

    for map_id in map_task_ids:
        try:
            map_output_key = f"map_output_taobao/{map_id}.json"
            obj = bucket.get_object(map_output_key)
            content = obj.read().decode('utf-8')
            total_input_size += len(content.encode('utf-8'))
            map_data = json.loads(content)
            map_results.append(map_data)
        except Exception as e:
            pass

    read_time = time.time() - read_start

    # Aggregate hourly statistics
    aggregate_start = time.time()

    merged_hourly_stats = {}
    for hour in range(24):
        hour_str = f"{hour:02d}"
        merged_hourly_stats[hour_str] = {
            'pv': 0,
            'unique_users': 0,
            'buy': 0
        }

    total_records = 0

    for map_result in map_results:
        total_records += map_result.get('total_records', 0)

        hourly_stats = map_result.get('hourly_stats', {})
        for hour, stats in hourly_stats.items():
            merged_hourly_stats[hour]['pv'] += stats.get('pv', 0)
            merged_hourly_stats[hour]['unique_users'] += stats.get('unique_users', 0)
            merged_hourly_stats[hour]['buy'] += stats.get('buy', 0)

    aggregate_time = time.time() - aggregate_start

    # Calculate totals
    total_pv = sum(stats['pv'] for stats in merged_hourly_stats.values())
    total_uv = sum(stats['unique_users'] for stats in merged_hourly_stats.values())
    total_buy = sum(stats['buy'] for stats in merged_hourly_stats.values())

    # Prepare output JSON
    output_data = {
        'reduce_id': reduce_id,
        'maps_processed': len(map_results),
        'map_range': f"{map_task_ids[0]}-{map_task_ids[-1]}" if map_task_ids else "",
        'total_records': total_records,
        'total_pv': total_pv,
        'total_unique_users': total_uv,
        'total_buy': total_buy,
        'hourly_stats': merged_hourly_stats
    }

    # Write output to OSS
    write_start = time.time()
    output_key = f"reduce_output_taobao/{reduce_id}.json"
    try:
        bucket.put_object(output_key, json.dumps(output_data, ensure_ascii=False))
        write_time = time.time() - write_start
        output_size_bytes = len(json.dumps(output_data).encode('utf-8'))
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'reduce',
        'reduce_id': reduce_id,
        'output_file': output_key,
        'output_size_kb': round(output_size_bytes / 1024, 2),
        'maps_processed': len(map_results),
        'records_aggregated': total_records,
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'aggregate': round(aggregate_time, 4),
            'oss_write': round(write_time, 4)
        }
    }

def execute_final_reduce_taobao(event, context, start_time):
    """Final Reduce Task for Taobao: Generate global hourly traffic report"""
    reduce_task_ids = event.get('reduce_task_ids', [])

    if not reduce_task_ids:
        return {'statusCode': 400, 'error': 'Missing reduce_task_ids parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read Reduce outputs from OSS
    read_start = time.time()
    reduce_results = []

    for reduce_id in reduce_task_ids:
        try:
            reduce_output_key = f"reduce_output_taobao/{reduce_id}.json"
            obj = bucket.get_object(reduce_output_key)
            content = obj.read().decode('utf-8')
            reduce_data = json.loads(content)
            reduce_results.append(reduce_data)
        except Exception as e:
            pass

    read_time = time.time() - read_start

    # Global aggregation
    aggregate_start = time.time()

    global_hourly_stats = {}
    for hour in range(24):
        hour_str = f"{hour:02d}"
        global_hourly_stats[hour_str] = {
            'pv': 0,
            'unique_users': 0,
            'buy': 0,
            'conversion_rate': 0.0
        }

    global_total_records = 0
    global_total_pv = 0
    global_total_uv = 0
    global_total_buy = 0

    for reduce_result in reduce_results:
        global_total_records += reduce_result.get('total_records', 0)
        global_total_pv += reduce_result.get('total_pv', 0)
        global_total_uv += reduce_result.get('total_unique_users', 0)
        global_total_buy += reduce_result.get('total_buy', 0)

        hourly_stats = reduce_result.get('hourly_stats', {})
        for hour, stats in hourly_stats.items():
            global_hourly_stats[hour]['pv'] += stats.get('pv', 0)
            global_hourly_stats[hour]['unique_users'] += stats.get('unique_users', 0)
            global_hourly_stats[hour]['buy'] += stats.get('buy', 0)

    # Calculate conversion rates
    for hour, stats in global_hourly_stats.items():
        if stats['pv'] > 0:
            stats['conversion_rate'] = round(stats['buy'] / stats['pv'], 6)

    # Find peak and lowest hours
    peak_hour = max(global_hourly_stats.items(), key=lambda x: x[1]['pv'])
    lowest_hour = min(global_hourly_stats.items(), key=lambda x: x[1]['pv'])

    aggregate_time = time.time() - aggregate_start

    # Prepare final output
    final_output = {
        'analysis_type': 'hourly_traffic',
        'total_records': global_total_records,
        'total_pv': global_total_pv,
        'total_unique_users': global_total_uv,
        'total_buy': global_total_buy,
        'global_conversion_rate': round(global_total_buy / global_total_pv, 6) if global_total_pv > 0 else 0,
        'hourly_breakdown': global_hourly_stats,
        'insights': {
            'peak_hour': peak_hour[0],
            'peak_pv': peak_hour[1]['pv'],
            'lowest_hour': lowest_hour[0],
            'lowest_pv': lowest_hour[1]['pv'],
            'peak_to_lowest_ratio': round(peak_hour[1]['pv'] / lowest_hour[1]['pv'], 2) if lowest_hour[1]['pv'] > 0 else 0
        }
    }

    # Write final output to OSS
    write_start = time.time()
    output_key = "final_result_taobao.json"
    try:
        bucket.put_object(output_key, json.dumps(final_output, ensure_ascii=False, indent=2))
        write_time = time.time() - write_start
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'final_reduce',
        'output_file': output_key,
        'total_records_analyzed': global_total_records,
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'aggregate': round(aggregate_time, 4),
            'oss_write': round(write_time, 4)
        }
    }

# ========== Original Log Analysis Handlers (for backward compatibility) ==========

def execute_map(event, context, start_time):
    """Execute Map task: read CSV from OSS, extract statistics, write output to OSS"""
    task_id = event.get('task_id', 'unknown')
    input_file = event.get('input_file')

    if not input_file:
        return {'statusCode': 400, 'error': 'Missing input_file parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read CSV from OSS
    read_start = time.time()
    try:
        obj = bucket.get_object(input_file)
        csv_content = obj.read().decode('utf-8')
        input_size_bytes = len(csv_content.encode('utf-8'))
        read_time = time.time() - read_start
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to read from OSS: {str(e)}'}

    # Process CSV - extract statistics
    process_start = time.time()
    lines = csv_content.strip().split('\n')

    # Initialize statistics
    level_stats = defaultdict(int)
    exception_stats = defaultdict(int)
    source_stats = defaultdict(int)
    hour_distribution = defaultdict(int)
    total_records = 0

    # Parse CSV (format: file_id,line_id,timestamp,host,source,level,exception_type,description,raw_data)
    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue

        parts = line.split(',')
        if len(parts) >= 7:
            total_records += 1

            # Extract fields
            source = parts[4].strip() if len(parts) > 4 else 'unknown'
            level = parts[5].strip().upper() if len(parts) > 5 else 'UNKNOWN'
            exception_type = parts[6].strip() if len(parts) > 6 else ''

            # Statistics
            level_stats[level] += 1
            source_stats[source] += 1
            if exception_type:
                exception_stats[exception_type] += 1

            # Time distribution (extract hour from timestamp if available)
            try:
                if len(parts) > 2 and parts[2]:
                    timestamp_ms = int(parts[2])
                    hour = (timestamp_ms // 3600000) % 24
                    hour_distribution[f"hour_{hour}"] += 1
            except:
                pass

    process_time = time.time() - process_start

    # Prepare output JSON
    output_data = {
        'task_id': task_id,
        'input_file': input_file,
        'input_size_kb': round(input_size_bytes / 1024, 2),
        'total_records': total_records,
        'level_stats': dict(level_stats),
        'source_stats': dict(source_stats),
        'exception_stats': dict(exception_stats),
        'hour_distribution': dict(hour_distribution)
    }

    # Write output to OSS
    write_start = time.time()
    output_key = f"map_output/{task_id}.json"
    try:
        bucket.put_object(output_key, json.dumps(output_data, ensure_ascii=False))
        write_time = time.time() - write_start
        output_size_bytes = len(json.dumps(output_data).encode('utf-8'))
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'map',
        'task_id': task_id,
        'output_file': output_key,
        'output_size_kb': round(output_size_bytes / 1024, 2),
        'records_processed': total_records,
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'process': round(process_time, 4),
            'oss_write': round(write_time, 4)
        }
    }

def execute_reduce(event, context, start_time):
    """Execute Reduce task: read Map outputs from OSS, aggregate, write to OSS"""
    reduce_id = event.get('reduce_id', 'unknown')
    map_task_ids = event.get('map_task_ids', [])

    if not map_task_ids:
        return {'statusCode': 400, 'error': 'Missing map_task_ids parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read Map outputs from OSS
    read_start = time.time()
    map_results = []
    total_input_size = 0

    for map_id in map_task_ids:
        try:
            map_output_key = f"map_output/{map_id}.json"
            obj = bucket.get_object(map_output_key)
            content = obj.read().decode('utf-8')
            total_input_size += len(content.encode('utf-8'))
            map_data = json.loads(content)
            map_results.append(map_data)
        except Exception as e:
            pass

    read_time = time.time() - read_start

    # Aggregate statistics
    aggregate_start = time.time()

    total_level_stats = defaultdict(int)
    total_source_stats = defaultdict(int)
    total_exception_stats = defaultdict(int)
    total_hour_distribution = defaultdict(int)
    total_records = 0
    total_input_kb = 0

    for map_result in map_results:
        total_records += map_result.get('total_records', 0)
        total_input_kb += map_result.get('input_size_kb', 0)

        # Aggregate level stats
        for level, count in map_result.get('level_stats', {}).items():
            total_level_stats[level] += count

        # Aggregate source stats
        for source, count in map_result.get('source_stats', {}).items():
            total_source_stats[source] += count

        # Aggregate exception stats
        for exc, count in map_result.get('exception_stats', {}).items():
            total_exception_stats[exc] += count

        # Aggregate hour distribution
        for hour, count in map_result.get('hour_distribution', {}).items():
            total_hour_distribution[hour] += count

    aggregate_time = time.time() - aggregate_start

    # Prepare output JSON
    output_data = {
        'reduce_id': reduce_id,
        'maps_processed': len(map_results),
        'map_range': f"{map_task_ids[0]}-{map_task_ids[-1]}" if map_task_ids else "",
        'total_records': total_records,
        'total_input_kb': round(total_input_kb, 2),
        'total_level_stats': dict(total_level_stats),
        'total_source_stats': dict(total_source_stats),
        'total_exception_stats': dict(total_exception_stats),
        'total_hour_distribution': dict(total_hour_distribution)
    }

    # Write output to OSS
    write_start = time.time()
    output_key = f"reduce_output/{reduce_id}.json"
    try:
        bucket.put_object(output_key, json.dumps(output_data, ensure_ascii=False))
        write_time = time.time() - write_start
        output_size_bytes = len(json.dumps(output_data).encode('utf-8'))
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'reduce',
        'reduce_id': reduce_id,
        'output_file': output_key,
        'output_size_kb': round(output_size_bytes / 1024, 2),
        'maps_processed': len(map_results),
        'records_aggregated': total_records,
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'aggregate': round(aggregate_time, 4),
            'oss_write': round(write_time, 4)
        }
    }

def execute_final_reduce(event, context, start_time):
    """Execute Final Reduce task: read all Reduce outputs from OSS, generate global summary"""
    reduce_task_ids = event.get('reduce_task_ids', [])

    if not reduce_task_ids:
        return {'statusCode': 400, 'error': 'Missing reduce_task_ids parameter'}

    # OSS configuration
    access_key_id = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')'
    access_key_secret = 'os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')'
    endpoint = 'oss-cn-hangzhou-internal.aliyuncs.com'
    bucket_name = os.environ.get('OSS_BUCKET', 'mapreduce-experiment')

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # Read Reduce outputs from OSS
    read_start = time.time()
    reduce_results = []

    for reduce_id in reduce_task_ids:
        try:
            reduce_output_key = f"reduce_output/{reduce_id}.json"
            obj = bucket.get_object(reduce_output_key)
            content = obj.read().decode('utf-8')
            reduce_data = json.loads(content)
            reduce_results.append(reduce_data)
        except Exception as e:
            pass

    read_time = time.time() - read_start

    # Global aggregation
    aggregate_start = time.time()

    global_level_stats = defaultdict(int)
    global_source_stats = defaultdict(int)
    global_exception_stats = defaultdict(int)
    global_hour_distribution = defaultdict(int)
    global_total_records = 0
    global_total_input_kb = 0

    for reduce_result in reduce_results:
        global_total_records += reduce_result.get('total_records', 0)
        global_total_input_kb += reduce_result.get('total_input_kb', 0)

        # Aggregate level stats
        for level, count in reduce_result.get('total_level_stats', {}).items():
            global_level_stats[level] += count

        # Aggregate source stats
        for source, count in reduce_result.get('total_source_stats', {}).items():
            global_source_stats[source] += count

        # Aggregate exception stats
        for exc, count in reduce_result.get('total_exception_stats', {}).items():
            global_exception_stats[exc] += count

        # Aggregate hour distribution
        for hour, count in reduce_result.get('total_hour_distribution', {}).items():
            global_hour_distribution[hour] += count

    # Calculate percentages
    level_percentages = {}
    if global_total_records > 0:
        for level, count in global_level_stats.items():
            level_percentages[level] = round(count / global_total_records * 100, 2)

    # Top exceptions
    top_exceptions = sorted(global_exception_stats.items(), key=lambda x: x[1], reverse=True)[:10]

    aggregate_time = time.time() - aggregate_start

    # Prepare final output
    final_output = {
        'task_type': 'final_reduce',
        'reduces_processed': len(reduce_results),
        'total_records': global_total_records,
        'total_input_kb': round(global_total_input_kb, 2),
        'total_input_mb': round(global_total_input_kb / 1024, 2),
        'global_level_distribution': dict(global_level_stats),
        'level_percentages': level_percentages,
        'global_source_distribution': dict(global_source_stats),
        'top_exceptions': [{'exception': exc, 'count': count} for exc, count in top_exceptions],
        'hourly_distribution': dict(global_hour_distribution)
    }

    # Write final output to OSS
    write_start = time.time()
    output_key = "final_result.json"
    try:
        bucket.put_object(output_key, json.dumps(final_output, ensure_ascii=False, indent=2))
        write_time = time.time() - write_start
    except Exception as e:
        return {'statusCode': 500, 'error': f'Failed to write final result to OSS: {str(e)}'}

    total_time = time.time() - start_time

    return {
        'statusCode': 200,
        'task_type': 'final_reduce',
        'output_file': output_key,
        'total_records': global_total_records,
        'reduces_processed': len(reduce_results),
        'timing': {
            'total': round(total_time, 4),
            'oss_read': round(read_time, 4),
            'aggregate': round(aggregate_time, 4),
            'oss_write': round(write_time, 4)
        },
        'summary': final_output
    }
