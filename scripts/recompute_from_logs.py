#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify reported results directly from the included raw logs.

No cloud account is required. This script recomputes, for each of the six
solutions, the execution time and the cost from the per-task timing records
stored in run_*/map_results.json and run_*/reduce_results.json, and compares
them with the values predicted by the calibrated model.

Cost model (Alibaba Cloud FC, CU billing, calibrated):
    CU price          : 0.00011 CNY per CU (verified against the console bill)
    vCPU conversion   : vCPU seconds        -> 1.00 CU per vCPU*s
    memory conversion : memory GB seconds   -> 0.15 CU per GB*s
    vCPU:memory ratio : 2:3  (0.667 vCPU per GB, derived from the console bill)
    invocation        : 75 CU per 10,000 calls (0.0075 CU per call)

The billed cost of a run is therefore:

    cost = (vCPU_s + 0.15 * GB_s + 0.0075 * calls) * 0.00011  [CNY]

where vCPU_s = 0.667 * GB_s, and GB_s is the sum over all function instances
of (memory_GB * billed duration seconds), i.e. the per-instance execution
time recorded in the logs (the platform does not bill scheduling overhead).
"""
import json
import os
import statistics

CU_PRICE = 0.00011
MEM_CU = 0.15
VCPU_PER_GB = 0.667
INV_CU = 75 / 10000.0

# Calibrated model prediction for each solution: (map_mem_mb, pred_time_s, pred_cost_cny)
SOLUTIONS = {
    1: (512,  23.12, 0.03390),
    2: (640,  19.69, 0.03461),
    3: (768,  17.23, 0.03485),
    4: (1024, 14.13, 0.0353),
    5: (1280, 11.99, 0.0344),
    6: (1536, 11.36, 0.0378),
}


def task_sum(path):
    data = json.load(open(path, encoding='utf-8'))
    total = 0.0
    calls = 0
    for item in data:
        if item.get('success') and 'timing' in item.get('result', {}):
            total += item['result']['timing'].get('total', 0.0)
            calls += 1
    return total, calls


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    sol_dir = os.path.join(os.path.dirname(base), 'solutions')
    print(f"{'Sol':>3} {'mem':>6} {'time(mean)':>10} {'pred_t':>7} {'T err':>7} "
          f"{'cost(mean)':>10} {'pred_c':>8} {'C err':>7}")
    for name in sorted(os.listdir(sol_dir)):
        if not name.startswith('solution_'):
            continue
        sid = int(name.split('_')[1])
        mem, pred_t, pred_c = SOLUTIONS[sid]
        d = os.path.join(sol_dir, name)
        times, costs = [], []
        for k in range(1, 4):
            run = os.path.join(d, f'run_{k}')
            mt, mcalls = task_sum(os.path.join(run, 'map_results.json'))
            rt, rcalls = task_sum(os.path.join(run, 'reduce_results.json'))
            gbs = (mem / 1024.0) * mt + 0.5 * rt          # map mem + 512MB reducer
            calls = mcalls + rcalls
            cu = VCPU_PER_GB * gbs + MEM_CU * gbs + INV_CU * calls
            costs.append(cu * CU_PRICE)
            timing = json.load(open(os.path.join(run, 'timing.json'), encoding='utf-8'))
            times.append(timing['map_wall'] + timing['reduce_wall'])
        t_med = statistics.mean(times)
        c_med = statistics.mean(costs)
        terr = abs(pred_t - t_med) / t_med * 100
        cerr = abs(pred_c - c_med) / c_med * 100
        print(f'{sid:>3} {mem:>6} {t_med:>10.2f} {pred_t:>7.2f} {terr:>6.1f}% '
              f'{c_med * 100:>9.2f}分 {pred_c * 100:>7.2f}分 {cerr:>6.1f}%')


if __name__ == '__main__':
    main()
