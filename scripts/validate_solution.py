#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template for re-running one configuration on Alibaba Cloud Function Compute.

Prerequisites
-------------
1. An Alibaba Cloud account with Function Compute enabled (cn-hangzhou tested).
2. The 55 input CSV files (~3.6 GB in total) uploaded to an OSS bucket under
   prefix `input_taobao/` (see ../README.md for the preprocessing notes).
3. Deploy `function_code/index.py` as functions whose memory sizes equal the
   configuration to be tested, e.g.:
       taobao-universal-512mb    (memory 512 MB)
       taobao-universal-1536mb   (memory 1536 MB)
4. Export credentials as environment variables; do NOT hardcode them:
       export ALIBABA_CLOUD_ACCESS_KEY_ID=...
       export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...

Usage
-----
    python validate_solution.py --map-mem 512 --reduce-mem 512 --reduce-tasks 5

Protocol (as reported in the paper)
-----------------------------------
    * one warm-up execution (discarded),
    * three measured executions separated by 20 s,
    * the median of the three executions is reported.

Note: the platform is shared and its throughput varies by roughly +/-10%
between sessions; re-running on your own account may therefore yield times
that differ from the released logs by up to ~10-20% even with the same code.
All raw logs of this study are provided so that the reported numbers can be
verified directly without re-running anything.
"""
import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import fc2

REGION = 'cn-hangzhou'
SERVICE = 'taobao-analysis-service'
NUM_MAP_TASKS = 55


def make_client(account_id):
    return fc2.Client(
        endpoint=f'https://{account_id}.{REGION}.fc.aliyuncs.com',
        accessKeyID=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        accessKeySecret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
    )


def invoke(client, fn, payload):
    try:
        r = client.invoke_function(SERVICE, fn, payload=json.dumps(payload))
        res = json.loads(r.data.decode('utf-8'))
        return {'success': res.get('statusCode') == 200,
                'task_id': payload['task_id'], 'result': res}
    except Exception as e:
        return {'success': False, 'task_id': payload['task_id'], 'error': str(e)}


def map_tasks():
    return [{'task_id': f'map_{i:03d}', 'task_type': 'map', 'data_type': 'taobao',
             'input_file': f'input_taobao/map_{i:03d}.csv',
             'output_prefix': f'map_{i:03d}'} for i in range(1, NUM_MAP_TASKS + 1)]


def reduce_tasks(n):
    per = NUM_MAP_TASKS // n
    tasks = []
    for i in range(n):
        s = i * per + 1
        e = min(s + per - 1, NUM_MAP_TASKS)
        tasks.append({'task_id': f'reduce_{i+1:03d}', 'task_type': 'reduce',
                      'data_type': 'taobao', 'reduce_id': f'reduce_{i+1:03d}',
                      'map_task_ids': [f'map_{j:03d}' for j in range(s, e + 1)],
                      'output_file': f'reduce_output_test/reduce_{i+1:03d}.json'})
    return tasks


def run_phase(client, fn, tasks, workers):
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(invoke, client, fn, t) for t in tasks]
        for f in as_completed(futs):
            results.append(f.result())
    return time.time() - t0, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account-id', required=True)
    ap.add_argument('--map-mem', type=int, required=True)
    ap.add_argument('--reduce-mem', type=int, default=512)
    ap.add_argument('--reduce-tasks', type=int, default=5)
    ap.add_argument('--runs', type=int, default=3)
    args = ap.parse_args()

    client = make_client(args.account_id)
    fn_map = f'taobao-universal-{args.map_mem}mb'
    fn_red = f'taobao-universal-{args.reduce_mem}mb'

    print('warm-up ...')
    run_phase(client, fn_map, map_tasks(), 55)
    run_phase(client, fn_red, reduce_tasks(args.reduce_tasks), args.reduce_tasks)

    totals = []
    for k in range(1, args.runs + 1):
        wm, mres = run_phase(client, fn_map, map_tasks(), 55)
        wr, rres = run_phase(client, fn_red, reduce_tasks(args.reduce_tasks), args.reduce_tasks)
        ok = sum(1 for r in mres if r['success'])
        totals.append(wm + wr)
        print(f'run {k}: map {wm:.2f}s + reduce {wr:.2f}s = {wm + wr:.2f}s '
              f'(map tasks ok: {ok}/{NUM_MAP_TASKS})')
        time.sleep(20)

    print(f'median over {args.runs} runs: {statistics.median(totals):.2f}s')


if __name__ == '__main__':
    main()
