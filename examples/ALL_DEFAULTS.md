# Canonical all-omitted contract and Source Presumption

`DIGR：分析一个复杂技术方案并给出结论`

`DIGR()：分析一个复杂技术方案并给出结论`

Both surfaces are the all-omitted case because the invocation supplies no parameter token and no S/D/L marker. They therefore instantiate the fixed contract:

`DIGR(3,3min,5,1,S(3,1min,5,1),D(3),L(1))`

This is not an AUTO mode and is not workload-dependent semantic calibration. The fixed values are N=3, T=180s, R=5, B=1, S(n=3,t=60s,r=5,b=1), D=3 and L1.

If the user supplies any parameter or S/D/L marker, the invocation leaves the all-omitted branch. Partial omission then keeps the ordinary rules: B=0, b=0 and L1 are structural defaults, while missing N/T/R/n/t/r/s are completed semantically from U0 plus the explicit parameters.

Separately, normal DIGR execution presumes `SourceDisposition=REQUIRED`. The fixed `S(3,1min,5,1)` default does not replace the source-disposition rule. A waiver still requires a real task/host reason such as an explicitly closed transformation or a prohibition on external material.
