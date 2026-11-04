# Real-World Validation of ANSGA-II for Serverless MapReduce

This folder contains the complete code, configuration files, and experimental
results for the real-world case study presented in the paper
*A\*-Guided Multi-Objective Resource Allocation for Serverless MapReduce Job*.

ANSGA-II was deployed on **Alibaba Cloud Function Compute (FC)** and validated
with a real log-analysis MapReduce application. All input data, intermediate
results, and final outputs were stored in **Alibaba Cloud Object Storage
Service (OSS)**.

## Case Study at a Glance

| Item | Value |
|------|-------|
| Dataset | 28.02 MB web server access logs (100 CSV files, 7,400 records) |
| Platform | Alibaba Cloud Function Compute, region cn-hangzhou |
| Runtime | Python 3.9 |
| Instance | 28 nodes, 91 edges |
| Decision variables | Mapper memory, Mapper concurrency, objects per Reducer, Coordinator memory, Reducer memory |
| Encoding space | 7 memory options, 5 concurrency levels (10-100), 5 reducer strategies |
| Pareto solutions | 5 |
| Deployment errors | below 11% for both makespan and cost |
| Best solution | 0.98% makespan error, 5.54% cost error |

## Repository Structure

```
case_study_validation/
├── config/
│   └── aliyun_config.json.template   # Copy to aliyun_config.json and fill in credentials
├── data/
│   ├── input/                        # 100 CSV input files (28.02 MB) uploaded to OSS
│   └── output/                       # OSS results: 100 map + 31 reduce JSON files
├── function_code/
│   └── index.py                      # Map / Reduce / Final-Reduce handler deployed to FC
├── instance/
│   ├── Cloud223N28MBReal.txt         # DAG instance (28 nodes, 91 edges)
│   └── generate_nsga_instance.py     # Instance generator
├── results/
│   ├── pareto_front_28MB.csv         # Five Pareto optimal solutions (cost, makespan)
│   ├── pareto_solutions_detailed.csv # Decoded configurations of each solution
│   ├── all_pareto_paths_28MB.txt     # Full paths of the Pareto front
│   ├── path_details_28MB.txt         # Representative min-cost / min-makespan paths
│   └── solution3_validation_result.json # Detailed deployment measurements
├── scripts/
│   ├── deploy_solution1.py           # Deploy Solution 1 (192 MB, 50 concurrency)
│   ├── deploy_solution3.py           # Deploy Solution 3 (128 MB, 100 concurrency)
│   ├── deploy_solutions_245.py       # Batch deployment for Solutions 2, 4, 5
│   ├── validate_solution1.py         # Deploy-and-measure validation
│   ├── validate_solution3.py
│   ├── validate_solutions_245.py     # Batch validation
│   ├── calculate_cost.py             # Cost calculation from measured runtime
│   ├── calibrate_model.py            # Calibrate processing-speed parameter
│   └── calibrate_cost.py             # Calibrate cost parameter
├── LICENSE
├── requirements.txt
└── README.md
```

## Input Data

The `data/input/` folder contains the 100 CSV files (28.02 MB in total) that
were uploaded to OSS and processed by the MapReduce job. Each file has the
following columns:

`file_id, line_id, timestamp, host, source, level, exception_type, description, raw_data`

The `data/output/` folder contains the JSON files written back to OSS during
the deployment experiments: `map_output/` holds the per-file statistics
produced by the 100 Map tasks, and `reduce_output/` holds the aggregated
results of the Reduce tasks.

## Pareto Solutions

| Solution | Mapper Memory (MB) | Mapper Concurrency | Objects per Reducer | Coordinator Memory (MB) | Reducer Memory (MB) |
|----------|--------------------|--------------------|---------------------|-------------------------|---------------------|
| 1 | 192 | 50 | 5 | 512 | 128 |
| 2 | 192 | 25 | 50 | 512 | 128 |
| 3 | 128 | 100 | 25 | 512 | 128 |
| 4 | 192 | 10 | 10 | 512 | 128 |
| 5 | 256 | 75 | 25 | 512 | 128 |

## Validation Results

Three representative solutions were deployed on Alibaba Cloud FC:

| Solution | Computed Makespan (s) | Measured Makespan (s) | Makespan Error | Computed Cost (CNY) | Measured Cost (CNY) | Cost Error |
|----------|----------------------|----------------------|----------------|---------------------|---------------------|------------|
| 1 | 10.52 | 9.91 | 5.80% | 0.000287 | 0.000271 | 5.67% |
| 3 | 10.08 | 9.98 | 0.98% | 0.000182 | 0.000196 | 7.13% |
| 4 | 14.07 | 12.59 | 10.50% | 0.000247 | 0.000261 | 5.54% |

The remaining errors stem from cloud-platform uncertainties such as cold-start
latency, network jitter, and dynamic resource contention.

## How to Reproduce

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp config/aliyun_config.json.template config/aliyun_config.json
# Edit config/aliyun_config.json with your Alibaba Cloud credentials
```

The function code reads credentials from the environment variables
`OSS_ACCESS_KEY_ID` and `OSS_ACCESS_KEY_SECRET`.

### 3. Deploy the functions

```bash
cd scripts
python deploy_solution3.py
```

### 4. Run the validation

```bash
python validate_solution3.py
```

### 5. Compute the cost

```bash
python calculate_cost.py
```

## License

MIT License. See `LICENSE` for details.
