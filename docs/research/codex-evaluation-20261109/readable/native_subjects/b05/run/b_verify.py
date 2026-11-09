"""Independent checks of Main, bounded D, and the sufficient-summary algebra."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from random import Random
import json
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = load("main_budget_candidate", ROOT / "portfolio/task2_budget/output/budget.py")
bounded = load("bounded_budget", ROOT / "run/b_budget_bounded.py")
algebra = load("ledger_algebra", ROOT / "run/b_relation_monoid.py")


def oracle(rows, categories):
    """Deliberately direct O(n^2) specification reading, not an optimized index."""
    result = {"used": dict.fromkeys(categories, 0), "unassigned": 0, "ignored_transfers": 0}
    def category(row):
        unique = set(row["category_candidates"])
        return next(iter(unique)) if len(unique) == 1 and next(iter(unique)) in categories else None
    for row in rows:
        amount = row["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount")
        kind = row["type"]
        if kind == "transfer":
            result["ignored_transfers"] += 1
            continue
        if kind == "expense":
            target = category(row)
        else:
            matches = [x for x in rows if x["type"] == "expense" and x["id"] == row["refund_of"]]
            target = category(matches[0]) if len(matches) == 1 else None
            amount = -amount
        if target is None:
            result["unassigned"] += amount
        else:
            result["used"][target] += amount
    return result


rng = Random(90137)
for trial in range(1200):
    categories = rng.sample(["food", "travel"], rng.randrange(3))
    rows = []
    for _ in range(rng.randrange(15)):
        kind = rng.choice(["expense", "refund", "transfer"])
        row = {"id": rng.choice(["x", "y", "z"]), "type": kind, "amount": rng.randrange(101),
               "category_candidates": [rng.choice(["food", "travel", "unknown"]) for _ in range(rng.randrange(4))]}
        if kind == "refund":
            row["refund_of"] = rng.choice(["x", "y", "z", "absent"])
        rows.append(row)
    frozen = deepcopy((rows, categories))
    expected = oracle(rows, categories)
    for module in (main, bounded):
        got = module.summarize(rows, categories)
        assert got == expected, (trial, module.__name__, rows, categories, got, expected)
        # Result mutation must not affect inputs or later calls.
        got["used"]["new_key"] = 99
        assert module.summarize(rows, categories) == expected
    state = algebra.scan(rows, categories)
    assert algebra.finish(state) == expected
    a = rng.randrange(len(rows) + 1)
    b = rng.randrange(a, len(rows) + 1)
    s1, s2, s3 = (algebra.scan(part, categories) for part in (rows[:a], rows[a:b], rows[b:]))
    snapshots = deepcopy((s1, s2, s3))
    left = algebra.merge(algebra.merge(s1, s2), s3)
    right = algebra.merge(s1, algebra.merge(s2, s3))
    assert left == right == state, ("associativity", trial)
    assert algebra.merge(s1, s2) == algebra.merge(s2, s1), ("commutativity", trial)
    assert (s1, s2, s3) == snapshots
    shuffled = list(rows)
    rng.shuffle(shuffled)
    assert bounded.summarize(shuffled, categories) == expected
    assert algebra.scan(shuffled, categories) == state
    assert (rows, categories) == frozen
    assert sum(expected["used"].values()) + expected["unassigned"] == sum(
        r["amount"] * (1 if r["type"] == "expense" else -1)
        for r in rows if r["type"] != "transfer")

for module in (main, bounded):
    for amount in (True, False, -1, 1.0, "1", None):
        for kind in ("transfer", "expense", "refund"):
            row = {"id": "x", "type": kind, "amount": amount,
                   "refund_of": "x", "category_candidates": ["food"]}
            try:
                module.summarize([row], ["food"])
            except ValueError:
                pass
            else:
                raise AssertionError((module.__name__, kind, amount))

# Distinguishing prefixes show why absent and singleton(None) cannot be merged.
unknown = [{"id": "x", "type": "expense", "amount": 0, "category_candidates": []}]
known = [{"id": "x", "type": "expense", "amount": 100, "category_candidates": ["food"]}]
refund = [{"id": "r", "type": "refund", "amount": 30, "refund_of": "x"}]
empty_state, unknown_state = algebra.scan([], ["food"]), algebra.scan(unknown, ["food"])
assert algebra.finish(empty_state) == algebra.finish(unknown_state)
empty_extension = algebra.finish(algebra.merge(empty_state, algebra.scan(known + refund, ["food"])))
unknown_extension = algebra.finish(algebra.merge(unknown_state, algebra.scan(known + refund, ["food"])))
assert empty_extension != unknown_extension

# The data itself is created before tracing; measure only function allocation.
large = [{"id": "x", "type": "expense", "amount": 1, "category_candidates": ["food"]}
         for _ in range(30000)] + refund
memory = {}
for module in (main, bounded):
    tracemalloc.start()
    result = module.summarize(large, ["food"])
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result == {"used": {"food": 30000}, "unassigned": -30, "ignored_transfers": 0}
    memory[module.__name__] = {"peak_allocated_bytes": peak}

print(json.dumps({"algebra_and_candidate_comparisons": "passed",
                  "new_minimal_distinction": {"absent_then_extension": empty_extension,
                                              "unclassifiable_singleton_then_extension": unknown_extension},
                  "duplicate_heavy_memory_probe": memory}, ensure_ascii=False, indent=2))
