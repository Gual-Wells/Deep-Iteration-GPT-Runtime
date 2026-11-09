"""Defective starter. Repair into output/budget.py."""
def summarize(items, categories):
    used = dict.fromkeys(categories, 0)
    unassigned = 0
    ignored = 0
    seen = {}
    for item in items:
        amount = item["amount"]
        if not isinstance(amount, int) or amount < 0:
            raise ValueError("amount")
        kind = item["type"]
        if kind == "transfer":
            ignored += amount
            continue
        candidates = item.get("category_candidates", [])
        category = next((c for c in candidates if c in categories), None)
        if kind == "refund":
            prior = seen.get(item["refund_of"])
            category = category or (prior and prior.get("category_candidates", [None])[0])
            amount = -amount
        else:
            seen[item["id"]] = item
        if category in used:
            used[category] = max(0, used[category] + amount)
        else:
            unassigned = max(0, unassigned + amount)
    return {"used": used, "unassigned": unassigned, "ignored_transfers": ignored}
