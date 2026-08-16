"""Mechanical evidence checks for DIGR D isolation levels.

The host establishes facts.  This helper merely prevents implementation labels
(e.g. "handoff", "nested run", "second agent", "worktree") from being treated
as isolation proof by themselves.
"""
from __future__ import annotations
from dataclasses import dataclass
from .validation import require_bool, require_isolation_level

@dataclass(frozen=True)
class IsolationFacts:
    semantic_firewall: bool
    separate_llm_history: bool = False
    controlled_telemetry_only: bool = False
    latent_d_state_hidden_from_main: bool = False
    application_state_isolated_or_filtered: bool = False
    independent_agent_identity: bool = False
    independent_instructions: bool = False
    independent_execution_loop: bool = False
    independent_tool_execution: bool = False

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            require_bool(name, getattr(self, name))

    @property
    def L1(self) -> bool:
        return self.semantic_firewall

    @property
    def L2(self) -> bool:
        return all((
            self.L1,
            self.separate_llm_history,
            self.controlled_telemetry_only,
            self.latent_d_state_hidden_from_main,
            self.application_state_isolated_or_filtered,
        ))

    @property
    def L3(self) -> bool:
        return all((
            self.L2,
            self.independent_agent_identity,
            self.independent_instructions,
            self.independent_execution_loop,
            self.independent_tool_execution,
        ))

    @property
    def max_claimable_level(self) -> int | None:
        if self.L3:
            return 3
        if self.L2:
            return 2
        if self.L1:
            return 1
        return None


def level_is_supported(target: int, facts: IsolationFacts) -> bool:
    require_isolation_level('target', target)
    if not isinstance(facts, IsolationFacts):
        raise TypeError('facts must be IsolationFacts')
    return facts.max_claimable_level == target
