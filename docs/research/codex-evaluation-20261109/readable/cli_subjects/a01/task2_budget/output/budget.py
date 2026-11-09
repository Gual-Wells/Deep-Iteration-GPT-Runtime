"""Summarize expenses and refunds against the supplied category catalog."""


def summarize(items, categories):
    """Return category totals without modifying any input objects."""
    used = dict.fromkeys(categories, 0)
    unassigned = 0
    ignored_transfers = 0
    expenses_by_id = {}

    for item in items:
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a nonnegative int, excluding bool")

        if item["type"] == "expense":
            candidates = set(item["category_candidates"])
            category = next(iter(candidates)) if len(candidates) == 1 else None
            if category not in used:
                category = None
            expenses_by_id.setdefault(item["id"], []).append(category)
            if category is None:
                unassigned += amount
            else:
                used[category] += amount
        elif item["type"] == "transfer":
            ignored_transfers += 1

    for item in items:
        if item["type"] != "refund":
            continue
        matches = expenses_by_id.get(item["refund_of"], ())
        category = matches[0] if len(matches) == 1 else None
        if category is None:
            unassigned -= item["amount"]
        else:
            used[category] -= item["amount"]

    return {
        "used": used,
        "unassigned": unassigned,
        "ignored_transfers": ignored_transfers,
    }
