"""Research model: sufficient, mergeable summaries for unordered ledger bags."""


def _category(row, directory):
    choices = set(row["category_candidates"])
    if len(choices) == 1:
        value = next(iter(choices))
        if value in directory:
            return value
    return None


def scan(rows, categories):
    used = dict.fromkeys(categories, 0)
    state = {"used": used, "unassigned": 0, "ignored_transfers": 0,
             "sources": {}, "refunds": {}}
    for row in rows:
        amount = row["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount")
        kind = row["type"]
        if kind == "expense":
            category = _category(row, used)
            key = row["id"]
            state["sources"][key] = ((2, None) if key in state["sources"] else (1, category))
            if category is None:
                state["unassigned"] += amount
            else:
                used[category] += amount
        elif kind == "refund":
            key = row["refund_of"]
            state["refunds"][key] = state["refunds"].get(key, 0) + amount
        else:
            state["ignored_transfers"] += 1
    return state


def merge(left, right):
    """Both states use the same category directory; neither argument is changed."""
    sources = dict(left["sources"])
    for key, value in right["sources"].items():
        sources[key] = (2, None) if key in sources else value
    refunds = dict(left["refunds"])
    for key, amount in right["refunds"].items():
        refunds[key] = refunds.get(key, 0) + amount
    return {"used": {c: left["used"][c] + right["used"][c] for c in left["used"]},
            "unassigned": left["unassigned"] + right["unassigned"],
            "ignored_transfers": left["ignored_transfers"] + right["ignored_transfers"],
            "sources": sources, "refunds": refunds}


def finish(state):
    used = dict(state["used"])
    unassigned = state["unassigned"]
    for key, amount in state["refunds"].items():
        count, category = state["sources"].get(key, (0, None))
        if count == 1 and category is not None:
            used[category] -= amount
        else:
            unassigned -= amount
    return {"used": used, "unassigned": unassigned,
            "ignored_transfers": state["ignored_transfers"]}
