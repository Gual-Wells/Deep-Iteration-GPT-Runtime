# Multiple S aggregation

Suppose three actual source loops complete:

- S1: n=5, r=3, source interval [0, 10]
- S2: n=4, r=6, source interval [5, 20]
- S3: n=7, r=4, source interval [30, 40]

Then proof uses `S₃`; `n_actual=4`, `r_actual=3`; source time is the union of all source-active intervals, not the sum of overlapping work: [0,20] + [30,40].
