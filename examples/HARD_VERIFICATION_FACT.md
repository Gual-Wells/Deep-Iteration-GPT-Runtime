# Hard observed time is not hard proof

A runtime may honestly observe 650 seconds of monotonic work for a `T=600s, B=1` contract, yet lose continuity identity before it can prove the interval. Internally the observed number may remain available for diagnostics, but the canonical hard proof must render `600s/?`, and the mechanical hard stop must remain false.
