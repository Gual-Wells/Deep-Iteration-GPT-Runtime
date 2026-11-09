"""Summarize a complete batch without changing its records."""


def summarize(items, categories):
    used = dict.fromkeys(categories, 0)

    def expense_category(item):
        candidates = set(item["category_candidates"])
        if len(candidates) == 1:
            category = next(iter(candidates))
            if category in used:
                return category
        return None

    expenses = {}
    for item in items:
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a nonnegative integer")
        if item["type"] == "expense":
            expenses.setdefault(item["id"], []).append(expense_category(item))

    unassigned = 0
    ignored_transfers = 0
    for item in items:
        kind = item["type"]
        if kind == "transfer":
            ignored_transfers += 1
            continue
        amount = item["amount"]
        if kind == "expense":
            category = expense_category(item)
        else:
            matches = expenses.get(item["refund_of"], [])
            category = matches[0] if len(matches) == 1 else None
            amount = -amount
        if category is None:
            unassigned += amount
        else:
            used[category] += amount

    return {
        "used": used,
        "unassigned": unassigned,
        "ignored_transfers": ignored_transfers,
    }
