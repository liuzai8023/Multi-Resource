# Real-World Case Study: Serverless MapReduce Resource Allocation on Alibaba Cloud

This folder contains the complete, reproducible evidence for the real-world case
study of the paper: **A\*-Guided Multi-Objective Resource Allocation for
Serverless MapReduce Jobs**.

The study deploys MapReduce jobs over **3.6 GB of Taobao user-behavior logs**
(100,150,807 records in 55 CSV files) on **Alibaba Cloud Function Compute (FC)**
in the cn-hangzhou region, and validates the makespan and cost predictions of
the ANSGA-II framework against measured executions and the platform's recorded
usage.

## Key numbers

| Item | Value |
|------|-------|
| Input data | 3.6 GB, 55 CSV files, 100,150,807 records |
| Map tasks per run | 55 (one per CSV file), concurrency 55 |
| Reduce tasks per run | 5 (objects per reducer = 11) |
| Mapper memory range | 512 - 1536 MB |
| Validated configurations | 6 (512, 640, 768, 1024, 1280, 1536 MB; one per memory tier) |
| Executions per configuration | 3 measured runs (after 1 warm-up) |
| Pareto-optimal solutions of the DAG | 6 (over 648 feasible paths) |
| Predicted vs measured time accuracy | 95.1% - 99.8% (average 97.7%) |
| Predicted vs measured cost accuracy | 89.0% - 100.0% (average 95.0%) |
| Platform charge per run | approximately 3.4-3.8 fen (0.034-0.038 CNY) |

### Validation scope

The Pareto front (six solutions across the 512-1536 MB configuration space: three memory
tiers, 512, 1280 and 1536 MB, each with two reduce-granularity variants) is computed from
the calibrated DAG model (see `instance/` and `analysis/pareto_front.txt`, and re-derivable
with `scripts/enumerate_front.py`). Six representative configurations spanning 512-1536 MB
(one per memory tier, in the 5-reduce-task variant) were deployed and validated with three
runs each. All reported accuracy figures refer to these six deployed configurations; the
three front tiers (512, 1280 and 1536 MB) are included in the validated set.

## Directory layout

```
CIE_case_study_final/
├── README.md                     this file
├── solutions/                    6 validated configurations, 3 runs each
│   ├── solution_1_512mb/
│   │   ├── config.json
│   │   ├── summary.json          run times, mean, prediction, accuracy
│   │   ├── run_1/
│   │   │   ├── timing.json       phase wall-clock times of the run
│   │   │   ├── map_results.json  55 map tasks, each with its own timing
│   │   │   └── reduce_results.json
│   │   ├── run_2/
│   │   └── run_3/
│   ├── solution_2_640mb/
│   ├── solution_3_768mb/
│   ├── solution_4_1024mb/
│   ├── solution_5_1280mb/
│   └── solution_6_1536mb/
├── calibration/                  per-memory-tier calibration runs
│   └── tier_{512,640,768,1024,1280,1536}mb/run_{1,2,3}/
├── instance/
│   └── TaobaoTraffic3.6GB_final.txt   the DAG instance solved by ANSGA-II
├── analysis/
│   ├── predicted_vs_measured.csv
│   ├── pareto_front.txt
│   ├── final_table.json
│   └── bill_verification.md      reconciliation with the console usage page
├── function_code/
│   └── index.py                  the deployed worker (map / reduce / final)
└── scripts/
    ├── recompute_from_logs.py    verify all reported numbers from the logs
    ├── enumerate_front.py        enumerate the 648 DAG paths and the exact front
    └── validate_solution.py      template to re-run a configuration on your account
```

## Reproducing the results

### Level 1 - verify from the released logs (no cloud account needed)

```bash
cd scripts
python recompute_from_logs.py     # recomputes times and costs from run_*/ logs
python enumerate_front.py         # enumerates 648 paths and the Pareto front
```

`recompute_from_logs.py` reproduces the reported execution times and charges
directly from the per-task timing records. The cost formula uses only official
FC billing items (see `analysis/bill_verification.md`):

```
CU      = vCPU_s + 0.15 * GB_s + 0.0075 * calls
vCPU_s  = 0.667 * GB_s              (vCPU:memory = 2:3, verified on the bill)
charge  = CU * 0.00011 CNY          (official unit price, verified on the bill)
```

### Level 2 - re-run on your own account

1. Upload the 55 CSV files to an OSS bucket under `input_taobao/`
   (the dataset is public: Taobao User Behavior Dataset, Tianchi).
2. Deploy `function_code/index.py` as FC functions whose memory sizes equal
   the configurations to test (e.g. `taobao-universal-512mb`).
3. Export your credentials as environment variables (never commit them) and run:

```bash
python validate_solution.py --account-id <YOUR_ACCOUNT_ID> \
    --map-mem 512 --reduce-mem 512 --reduce-tasks 5
```

Protocol: one warm-up execution (discarded) followed by three measured
executions separated by 20 s; the median is reported.

**Expected reproducibility:** the platform is shared and its throughput varies
by about +/-10% between sessions (and ~10-20% under sustained load). Re-runs may
therefore differ from the released logs by up to that amount even with
identical code and configurations. All raw logs are included so that the
reported numbers can be verified exactly without re-running anything.

## Cost model and platform findings

The paper's cost objective is computed with the FC CU billing structure. During
the case study we verified, against the console usage page, that

* the CU unit price is 0.00011 CNY/CU;
* vCPU is allocated proportionally to memory (0.667 vCPU per GB, i.e. 2 vCPU : 3 GB);
* a pure-CPU benchmark shows throughput scaling approximately with memory up to
  about 1536 MB and saturating beyond (elastic instances cap at about one vCPU).

A consequence is that the billed charge is nearly invariant to the memory
configuration for this CPU-bound workload (approximately 3.5 fen per run,
spread about +/-4%): taller memory tiers run proportionally faster. The
model-calibrated costs match the platform charge to within 8%. See
`analysis/bill_verification.md` for the full reconciliation.

## Notes

* Credentials are never included. `scripts/validate_solution.py` reads them from
  environment variables.
* The `.json` logs are the unmodified outputs of the deployed functions.
* Day of experiments: 2026-11-24 (Asia/Shanghai); region cn-hangzhou.

## Citation

If you use this data, please cite the paper.

## License

Released for research and review purposes.
