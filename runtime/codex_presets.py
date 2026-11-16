"""Named Codex depth defaults; no workload scheduler or semantic certification."""
from __future__ import annotations
from copy import deepcopy
import re
from typing import Any, Mapping

PRESETS = {
    "Light": {"N": 2, "R": 1, "D": 0, "V": 0, "L": 3, "M": 1},
    "Less": {"N": 6, "R": 2, "D": 1, "V": 1, "L": 3, "M": 1},
    "Default": {"N": 12, "R": 4, "D": 3, "V": 3, "L": 3, "M": 1},
    "More": {"N": 18, "R": 6, "D": 4, "V": 4, "L": 3, "M": 1},
    "Max": {"N": 24, "R": 8, "D": 6, "V": 6, "L": 3, "M": 1},
}
_NAMES = {name.casefold(): name for name in PRESETS}
_NAMES["standard"] = "Light"
_PUNCTUATION = str.maketrans({"（": "(", "）": ")", "，": ",", "＝": "="})


def preset_name(name: str) -> str:
    if not isinstance(name, str) or name.strip().casefold() not in _NAMES:
        raise ValueError("preset must be Light, Less, Default, More or Max")
    return _NAMES[name.strip().casefold()]


def _tokens(text: str) -> list[str]:
    depth, start, result = 0, 0, []
    for i, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced parameter group")
        elif char == "," and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    if depth:
        raise ValueError("unbalanced parameter group")
    result.append(text[start:].strip())
    return [token for token in result if token]


def _value(token: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"([A-Za-z]+)\s*(?:=\s*(.+)|\((.*)\))", token)
    return (match[1], (match[2] if match[2] is not None else match[3]).strip()) if match else None


def _merge(base: dict, values: Mapping[str, Any]) -> dict:
    result = deepcopy(base)
    for key, value in values.items():
        if key == "S" and isinstance(value, Mapping):
            result.setdefault("S", {}).update(deepcopy(dict(value)))
        else:
            result[key] = deepcopy(value)
    return result


def resolve_defaults(parameter_text: str = "", overrides: Mapping[str, Any] | None = None) -> dict:
    """Read named defaults/overrides while preserving unknown/positional text.

    T/t and source work are chosen for the actual task. This preview does not
    authorize work or replace the model's interpretation of unparsed fields.
    """
    if not isinstance(parameter_text, str):
        raise TypeError("parameter text must be str")
    text = parameter_text.translate(_PUNCTUATION).strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    selected, parsed, unparsed = [], {}, []
    for token in _tokens(text):
        pair = _value(token)
        candidate = pair[1] if pair and pair[0].casefold() == "preset" else token
        if candidate.casefold() in _NAMES:
            selected.append(preset_name(candidate))
            continue
        if pair and pair[0].casefold() == "preset":
            raise ValueError("unknown depth preset")
        if pair and pair[0] == "S":
            nested = {}
            for part in _tokens(pair[1]):
                entry = _value(part)
                if entry and entry[0] in ("n", "r", "b") and re.fullmatch(r"[0-9]+", entry[1]):
                    nested[entry[0]] = int(entry[1])
                elif entry and entry[0] == "t":
                    nested["t"] = entry[1]
                else:
                    unparsed.append("S." + part)
            parsed["S"] = nested
        elif pair and pair[0] in ("N", "R", "D", "V", "L", "M", "B") and re.fullmatch(r"[0-9]+", pair[1]):
            parsed[pair[0]] = int(pair[1])
        elif pair and pair[0] == "T":
            parsed["T"] = pair[1]
        elif pair and pair[0].casefold() in ("source", "target", "min"):
            # Preserve these semantic controls for the native task interpreter.
            unparsed.append(token)
        else:
            unparsed.append(token)
    if len(selected) > 1:
        raise ValueError("select exactly one depth preset")
    chosen = selected[0] if selected else "Default"
    values = _merge(PRESETS[chosen], parsed)
    if chosen == "Light":
        values = _merge({"T": 0, "B": 0, "S": {"n": 0, "t": 0, "r": 0, "b": 0}}, values)
    else:
        values.setdefault("B", 0)
    if overrides is not None:
        if not isinstance(overrides, Mapping):
            raise TypeError("overrides must be a mapping")
        values = _merge(values, overrides)
    for key in ("N", "R", "D", "V", "L", "M", "B"):
        value = values[key]
        if type(value) is not int or value < 0:
            raise ValueError(key + " must be a nonnegative integer")
    if values["L"] != 3:
        raise ValueError("Codex requires real native L3 at every preset")
    if values["M"] < 1 or values["B"] not in (0, 1):
        raise ValueError("M must be positive and B binary")
    return {"preset": chosen, "preset_explicit": bool(selected), "parameters": values,
            "parsed_overrides": parsed, "unparsed_tokens": unparsed,
            "source_default": "AUTO" if chosen == "Light" else "REQUIRED",
            "time_default": "TASK_DERIVED_SOFT" if chosen != "Light" else "ZERO_LOWER_BOUND",
            "scope": "Named parameter preview; unparsed text and real task conditions still require native interpretation"}


def preset_catalog() -> dict:
    return {"default": "Default", "presets": deepcopy(PRESETS),
            "aliases": {"standard": "Light"}, "L": "native L3 in every preset",
            "time": "T/t task-derived soft targets; Light/standard zero lower bound",
            "budget": "separate real authorization; no automatic paid allocation"}
