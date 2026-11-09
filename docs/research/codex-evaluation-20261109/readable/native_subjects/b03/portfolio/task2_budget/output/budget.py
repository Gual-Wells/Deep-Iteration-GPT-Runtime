"""Pure, order-independent budget totals for a supplied category catalog."""


def summarize(items, categories):
    used = dict.fromkeys(categories, 0)
    unassigned = 0
    ignored_transfers = 0
    expense_categories = {}

    def classify_expense(item):
        candidates = set(item["category_candidates"])
        if len(candidates) == 1:
            candidate = next(iter(candidates))
            if candidate in used:
                return candidate
        return None

    # Build the complete expense index before applying any refunds.
    for item in items:
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a nonnegative int, excluding bool")

        if item["type"] == "expense":
            category = classify_expense(item)
            expense_categories.setdefault(item["id"], []).append(category)
            if category is None:
                unassigned += amount
            else:
                used[category] += amount
        elif item["type"] == "transfer":
            ignored_transfers += 1

    for item in items:
        if item["type"] != "refund":
            continue
        matches = expense_categories.get(item["refund_of"], [])
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
