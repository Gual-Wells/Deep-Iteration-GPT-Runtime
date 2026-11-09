"""Summarize expenses and refunds against the supplied category directory."""


def _expense_category(item, known_categories):
    candidates = set(item["category_candidates"])
    if len(candidates) == 1:
        category = next(iter(candidates))
        if category in known_categories:
            return category
    return None


def summarize(items, categories):
    """Return net usage without modifying the records or category directory."""
    used = dict.fromkeys(categories, 0)
    known_categories = set(categories)
    expenses_by_id = {}

    # Index the complete batch so refunds may precede their original expense.
    # Keeping every match also preserves ambiguity from duplicate expense ids.
    for item in items:
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        if item["type"] == "expense":
            category = _expense_category(item, known_categories)
            expenses_by_id.setdefault(item["id"], []).append(category)

    unassigned = 0
    ignored_transfers = 0
    for item in items:
        kind = item["type"]
        if kind == "transfer":
            ignored_transfers += 1
            continue

        amount = item["amount"]
        if kind == "refund":
            matches = expenses_by_id.get(item["refund_of"], [])
            category = matches[0] if len(matches) == 1 else None
            amount = -amount
        else:
            category = _expense_category(item, known_categories)

        if category is None:
            unassigned += amount
        else:
            used[category] += amount

    return {
        "used": used,
        "unassigned": unassigned,
        "ignored_transfers": ignored_transfers,
    }
