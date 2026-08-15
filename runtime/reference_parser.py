"""Dependency-free reference parser for DIGR 2.2 invocation headers.
This is documentation-grade reference code, not a requirement that ChatGPT literally execute it.
"""
from __future__ import annotations
import re
from typing import Optional, TypedDict

class Invocation(TypedDict):
    enabled: bool
    task_raw: str
    min_prompt_iterations: Optional[int]
    complexity_budget: Optional[str]
    parameterized: bool

PARAM = re.compile(r"^深度迭代[（(]\s*(\d+)\s*[,，]\s*([^）)]+?)\s*[）)][：:]")
PLAIN = re.compile(r"^深度迭代[：:]")

def parse_invocation(message: str) -> Invocation:
    m = PARAM.match(message)
    if m:
        n = int(m.group(1))
        budget = m.group(2).strip()
        task = message[m.end():]
        enabled = n >= 1 and bool(budget) and bool(task.strip())
        return {"enabled": enabled, "task_raw": task if enabled else "", "min_prompt_iterations": n if enabled else None, "complexity_budget": budget if enabled else None, "parameterized": True}
    m = PLAIN.match(message)
    if m:
        task = message[m.end():]
        enabled = bool(task.strip())
        return {"enabled": enabled, "task_raw": task if enabled else "", "min_prompt_iterations": None, "complexity_budget": None, "parameterized": False}
    return {"enabled": False, "task_raw": "", "min_prompt_iterations": None, "complexity_budget": None, "parameterized": False}
