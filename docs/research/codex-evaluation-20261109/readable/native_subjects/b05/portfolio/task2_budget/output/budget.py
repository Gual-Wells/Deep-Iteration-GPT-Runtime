"""Summarize an unordered ledger using a bounded source state per expense id."""


def summarize(items, categories):
    used = dict.fromkeys(categories, 0)
    unassigned = 0
    ignored_transfers = 0
    source_category = {}
    multiple = object()

    # Amount validation remains prior to excluding a transfer. Positive expense
    # totals are independent of refund linkage, so each expense is classified once.
    for item in items:
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a nonnegative integer")
        kind = item["type"]
        if kind == "transfer":
            ignored_transfers += 1
        elif kind == "expense":
            choices = set(item["category_candidates"])
            category = next(iter(choices)) if len(choices) == 1 else None
            if category not in used:
                category = None
            key = item["id"]
            # Existence, rather than truthiness or amount, preserves both a zero
            # expense and an unclassifiable singleton as real source records.
            source_category[key] = multiple if key in source_category else category
            if category is None:
                unassigned += amount
            else:
                used[category] += amount

    # Only refunds need a complete relation. A second pass avoids retaining them
    # or their amounts in another index, including large orphan-refund batches.
    for item in items:
        if item["type"] == "refund":
            category = source_category.get(item["refund_of"])
            if category is None or category is multiple:
                unassigned -= item["amount"]
            else:
                used[category] -= item["amount"]

    return {"used": used, "unassigned": unassigned,
            "ignored_transfers": ignored_transfers}
