"""Public exploratory probe: relationship cardinality in an unordered budget ledger.
Run with Python -B. Does not read outside this subject or write portfolio output.
"""
from collections import defaultdict
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from itertools import permutations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
seed_path = ROOT / "portfolio/task2_budget/starter/budget.py"
spec = spec_from_file_location("budget_starter", seed_path)
seed = module_from_spec(spec)
spec.loader.exec_module(seed)


def classify(expense, categories):
    candidates = set(expense["category_candidates"])
    if len(candidates) == 1:
        candidate = next(iter(candidates))
        if candidate in categories:
            return candidate
    return None


def interpret(rows, categories):
    """Independent relation-first research model, not a delivery module."""
    relation = defaultdict(list)
    for row in rows:
        amount = row["amount"]
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("amount")
        if row["type"] == "expense":
            relation[row["id"]].append(row)
    buckets = dict.fromkeys(categories, 0)
    unassigned, transfers = 0, 0
    for row in rows:
        kind, amount = row["type"], row["amount"]
        if kind == "transfer":
            transfers += 1
            continue
        category = None
        if kind == "expense":
            category = classify(row, categories)
        elif kind == "refund":
            matches = relation[row["refund_of"]]
            if len(matches) == 1:
                category = classify(matches[0], categories)
            amount = -amount
        if category is None:
            unassigned += amount
        else:
            buckets[category] += amount
    return dict(used=buckets, unassigned=unassigned, ignored_transfers=transfers)


def expense(key="x", amount=100, candidates=("food",)):
    return dict(id=key, type="expense", amount=amount, category_candidates=list(candidates))


def refund(key="r", target="x", amount=30, candidates=("travel",)):
    # Its own plausible category deliberately conflicts with the actual source.
    return dict(id=key, type="refund", amount=amount, refund_of=target,
                category_candidates=list(candidates))


CATEGORIES = ["food", "travel"]
CASES = {
    "single_source": [expense(), refund()],
    "forward_reference_without_own_candidates": [expense(), refund(candidates=())],
    "zero_amount_duplicate_source": [expense(), refund(), expense(amount=0)],
    "unknown_candidate_is_still_a_competitor": [expense(amount=50, candidates=("food", "unknown", "food"))],
    "refund_exceeds_expense": [expense(amount=10), refund(amount=30)],
    "nonexpense_id_collisions_do_not_make_source_ambiguous": [
        expense(), refund(key="x"), dict(id="x", type="transfer", amount=7)],
}

results = {}
for name, rows in CASES.items():
    original = deepcopy(rows)
    expected = interpret(rows, CATEGORIES)
    seen = set()
    for order in permutations(rows):
        result = interpret(list(order), CATEGORIES)
        assert result == expected
        signed_total = sum(r["amount"] * (1 if r["type"] == "expense" else -1)
                           for r in rows if r["type"] != "transfer")
        assert sum(result["used"].values()) + result["unassigned"] == signed_total
        seen.add(json.dumps(seed.summarize(list(order), CATEGORIES), sort_keys=True))
    assert rows == original
    results[name] = {"relation_model": expected,
                     "starter_distinct_permutation_results": len(seen),
                     "starter_one_result": seed.summarize(rows, CATEGORIES)}

whole = interpret(CASES["single_source"], CATEGORIES)
separate = [interpret([r], CATEGORIES) for r in CASES["single_source"]]
results["partition_counterexample"] = {
    "whole": whole,
    "sum_of_finalized_parts": {
        "used": {c: sum(x["used"][c] for x in separate) for c in CATEGORIES},
        "unassigned": sum(x["unassigned"] for x in separate),
        "ignored_transfers": sum(x["ignored_transfers"] for x in separate),
    },
}
prefix_a, prefix_b = [expense(key="x")], [expense(key="y")]
suffix = [refund(candidates=())]
assert interpret(prefix_a, CATEGORIES) == interpret(prefix_b, CATEGORIES)
assert interpret(prefix_a + suffix, CATEGORIES) != interpret(prefix_b + suffix, CATEGORIES)
results["final_outputs_lose_relationship_information"] = {
    "same_prefix_result": interpret(prefix_a, CATEGORIES),
    "extension_for_id_x": interpret(prefix_a + suffix, CATEGORIES),
    "extension_for_id_y": interpret(prefix_b + suffix, CATEGORIES),
}
for bad in [True, False, -1, 1.0]:
    try:
        interpret([dict(id="t", type="transfer", amount=bad)], CATEGORIES)
    except ValueError:
        continue
    raise AssertionError(("accepted_bad_transfer_amount", bad))
results["validation_before_transfer_exclusion"] = "True, False, -1, 1.0 rejected"
print(json.dumps(results, ensure_ascii=False, indent=2))
