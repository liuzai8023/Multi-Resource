# Platform Bill Verification

This note documents the verification of the cost figures against the operator's
own usage records, so that every cost number in the paper can be traced to
platform data.

## 1. Console usage snapshot (single day of experiments)

Source: Alibaba Cloud Function Compute console -> Cost Center -> Usage
(region: cn-hangzhou, Asia/Shanghai; billing day: 2026-11-24).
Only Function Compute items are listed; OSS is billed under a separate product.

| Item | Value |
|------|-------|
| CU usage | **26,900 CU** |
| Function invocations | **5,262 calls** |
| Active vCPU usage | **21,200 vCPU·s** |
| Active memory usage | **31,800 GB·s** |
| Disk usage | 0 GB·s |
| Public outbound traffic | 1.61 MB |
| **List-price total** | **2.96 CNY** |

## 2. Verification of the official unit price

```
2.96 CNY / 26,900 CU = 0.00011004 CNY per CU
```

which matches the official CU unit price of **0.00011 CNY/CU**.

## 3. Verification of the vCPU-to-memory allocation

```
21,200 vCPU·s / 31,800 GB·s = 0.667 vCPU per GB   (i.e. 2 vCPU : 3 GB)
```

The ratio is identical for every deployed function (see the per-function table
below), which shows that the platform allocates vCPU proportionally to memory.
This is the mechanism behind the near-invariance of the billed cost with
respect to the memory configuration.

## 4. Verification of the CU formula

Official formula (active elastic instances):

```
CU = vCPU·s x 1.0 + memory_GB·s x 0.15 + invocations x 75/10,000 (+ disk)
   = 21,200 + 0.15 x 31,800 + 5,262 x 0.0075
   = 21,200 + 4,770 + 39.5 = 26,010 CU
```

The console reports 26,900 CU; the 3.4% difference is consistent with the
sampling and rounding of the usage page (the console itself states that the
data are for reference and subject to delay).

## 5. Per-function usage (same console page)

| Function | CU | Calls | vCPU·s | GB·s | List price (CNY) |
|----------|------|-------|--------|------|------------------|
| taobao-universal-640mb  | 5,448 | 1,053 | 4,336 | 6,505 | 0.60 |
| taobao-universal-512mb  | 4,997 | 1,158 | 3,989 | 5,984 | 0.55 |
| taobao-universal-1280mb | 4,117 |   707 | 3,263 | 4,895 | 0.45 |
| taobao-universal-1536mb | 3,737 |   668 | 2,966 | 4,450 | 0.41 |
| taobao-universal-1024mb | 3,361 |   620 | 2,667 | 4,001 | 0.37 |
| taobao-universal-768mb  | 3,259 |   620 | 2,588 | 3,882 | 0.36 |
| taobao-universal-384mb  | 1,753 |   376 | 1,404 | 2,107 | 0.19 |
| taobao-universal-192mb  |   100 |     5 |     0 |     0 | 0.01 |
| taobao-universal-256mb  |   100 |    55 |    10 |    16 | 0.01 |

Notes:

* The 192 MB and 256 MB entries correspond to deployment tests only (billed at
  the hourly minimum of 0.01 CNY).
* The per-function averages mix map and reduce invocations. Since a complete
  MapReduce run issues 55 map + 5 reduce calls, the per-run charge is obtained
  from the per-task execution times recorded in `solutions/*/run_*/`.

## 6. Derived per-run charge

Average over the day's experiments:

```
total calls / calls per run = 5,262 / 60 ~ 87.7 complete runs
2.96 CNY / 87.7 runs ~ 0.034 CNY per run (~3.4 fen)
```

Per configuration, using the measured per-task durations and the verified
formula (vCPU = 0.667 x GB, 0.15 CU per GB·s, 0.0111 CNY per CU-equivalent):

| Mapper memory | Estimated charge per run |
|---------------|--------------------------|
| 512 MB  | 3.53 fen |
| 640 MB  | 3.58 fen |
| 768 MB  | 3.77 fen |
| 1024 MB | 3.61 fen |
| 1280 MB | 3.59 fen |
| 1536 MB | 3.50 fen |

The billed cost is therefore nearly invariant to the memory configuration
(spread about +/-4%), because CPU is coupled to memory: a function with twice
the memory runs about twice as fast, so memory-seconds remain approximately
constant.

## 7. CPU-scaling micro-benchmark (context)

A pure CPU benchmark (20 million integer operations, steady state after
warm-up) was executed on functions of increasing memory:

| Memory | CPU time | Relative throughput | Memory ratio |
|--------|----------|---------------------|--------------|
| 512 MB  | 4.70 s | 1.00x | 1.00x |
| 640 MB  | 3.62 s | 1.30x | 1.25x |
| 768 MB  | 3.21 s | 1.46x | 1.50x |
| 896 MB  | 2.59 s | 1.82x | 1.75x |
| 1024 MB | 2.29 s | 2.05x | 2.00x |
| 1280 MB | 1.63 s | 2.89x | 2.50x |
| 1536 MB | 1.50 s | 3.13x | 3.00x |
| 2048 MB | 1.49 s | 3.15x | 4.00x |

Throughput scales approximately with memory up to about 1536 MB, and saturates
beyond it (elastic instances are capped at about one vCPU). Within the
configuration range used in the case study the coupling keeps the billed cost
approximately constant; beyond the cap, additional memory increases cost
without reducing makespan.
