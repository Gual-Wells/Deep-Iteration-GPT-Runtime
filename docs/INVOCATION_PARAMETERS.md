# Invocation Parameters

Public order is `N,T,R,B,S(n,t,r,b),D(s),V(o),L(e)`.

No group, empty group, `adaptive` or `profile=adaptive` leaves missing task-scale values for one native completion and defaults source policy to required. Only explicit `standard`/标准/`profile=standard` selects fixed N2/T0/R1/S0/D0/V0/L1/source-auto.

Typed labels may move. Flat `n,t,r,b,s,o,e` name S/D/V/L internals directly. Remove typed items, then map remaining bare tokens by type and relative order only when exactly one mapping exists. Duplicates, no solution and multiple solutions fail visibly.

A bare duration is soft T with B=0. `target=` is explicit soft and `min=` hard. B=1 or S(b=1) may leave time absent for positive native completion. Explicit values cannot be changed. Source policy `required|auto|off` composes with all V forms; off forces zero S values.
