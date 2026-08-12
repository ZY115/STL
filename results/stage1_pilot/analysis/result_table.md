# Stage I pilot result table

| Condition | Missed/trigger | Deadline/trigger | Terminal unresolved/trigger | Goal success | Return | Native cost/episode | STL cost/episode |
|---|---:|---:|---:|---:|---:|---:|---:|
| task_only | 0.2585 | 0.2072 | 0.0513 | 1.0000 | 23.9186 | 59.6760 | 1.7320 |
| native_cost | 0.2965 | 0.2488 | 0.0477 | 0.9880 | 15.8161 | 43.5380 | 1.3800 |
| gold_stl_cost | 0.2603 | 0.2066 | 0.0538 | 1.0000 | 23.4385 | 59.8680 | 1.7240 |

## Frozen primary comparisons

- Absolute safety reduction (task - gold): -0.0018
- Relative safety reduction: -0.0071
- Goal-success difference (gold - task): 0.0000
- Goal-success non-inferiority supported by 95% interval: True

N/A values are intentionally not replaced by zero. This pilot does not establish a formal safety guarantee.
