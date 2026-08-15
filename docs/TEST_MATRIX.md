# 2.3.0 Test Matrix

| Risk | Test / validation |
|---|---|
| T normalized or discretized by parser | `test_raw_T_is_preserved_not_normalized`, `test_parser_contains_no_time_tier_mapping` |
| T reference drifts from Sol 5.6 High | `test_manifest_reference_model` |
| Human-time semantics return | `test_no_legacy_human_time_definition` |
| Stop before T adequacy check | `test_stop_gate_orders_T_check_before_marginal_stop` |
| Mutable `stable` reused as immutable ref | `test_protocol_pin.py` |
| Missing manifest/core/schema files | `tests/validate_repo.py` |
| Python syntax regressions | `python -m py_compile ...` |
| Full parser/T/pin suite | `python -m unittest discover -s tests -v` |
