"""DIGR 5.0 Alpha 6 execution-precommitment integrity records.

This module does not decide task strategy. It validates a compact structured
commitment that the host/model is about to execute a repository-declared
component rather than understand-and-substitute it, and binds the next actual
attempt to that commitment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Mapping

from .protocol_pin import validate_repo_path
from .validation import require_nonempty_text, require_nonnegative_int

SCHEMA_VERSION = 1
MAX_REEDUCATION_ROUNDS = 2
_VALID_STATUS = {"SUCCEEDED", "FAILED"}


def _hex(name: str, value: object, n: int) -> str:
    text = require_nonempty_text(name, value).lower()
    if len(text) != n or any(c not in "0123456789abcdef" for c in text):
        raise ValueError(f"{name} must be {n} lowercase hex characters")
    return text


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class ExecutionCommitment:
    schema_version: int
    component_path: str
    component_blob_sha: str
    operation: str
    executor: str
    direct_execution: bool
    rejects_substitution: bool
    rejects_manual_result: bool
    reeducation_round: int = 0

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported execution commitment schema")
        object.__setattr__(self, "component_path", validate_repo_path(self.component_path))
        object.__setattr__(self, "component_blob_sha", _hex("component_blob_sha", self.component_blob_sha, 40))
        object.__setattr__(self, "operation", require_nonempty_text("operation", self.operation))
        object.__setattr__(self, "executor", require_nonempty_text("executor", self.executor))
        for name in ("direct_execution", "rejects_substitution", "rejects_manual_result"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        require_nonnegative_int("reeducation_round", self.reeducation_round)
        if self.reeducation_round > MAX_REEDUCATION_ROUNDS:
            raise ValueError("reeducation_round exceeds maximum")

    @property
    def accepted(self) -> bool:
        return self.direct_execution and self.rejects_substitution and self.rejects_manual_result

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def commitment_sha256(self) -> str:
        return _canonical_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ExecutionCommitment":
        return cls(
            d["schema_version"], d["component_path"], d["component_blob_sha"], d["operation"], d["executor"],
            d["direct_execution"], d["rejects_substitution"], d["rejects_manual_result"], d.get("reeducation_round", 0),
        )


@dataclass(frozen=True)
class InterrogationDecision:
    disposition: str
    next_round: int
    reason: str

    def __post_init__(self):
        if self.disposition not in ("ACCEPT", "REEDUCATE", "ABORT"):
            raise ValueError("invalid interrogation disposition")
        require_nonnegative_int("next_round", self.next_round)
        object.__setattr__(self, "reason", require_nonempty_text("reason", self.reason))


def interrogate(commitment: ExecutionCommitment) -> InterrogationDecision:
    if not isinstance(commitment, ExecutionCommitment):
        raise TypeError("commitment must be ExecutionCommitment")
    if commitment.accepted:
        return InterrogationDecision("ACCEPT", commitment.reeducation_round, "direct declared implementation execution committed")
    if commitment.reeducation_round < MAX_REEDUCATION_ROUNDS:
        return InterrogationDecision(
            "REEDUCATE", commitment.reeducation_round + 1,
            "declared implementation must be executed directly; substitution/manual result is not execution",
        )
    return InterrogationDecision("ABORT", commitment.reeducation_round, "execution-precommitment gate repeatedly failed")


@dataclass(frozen=True)
class ExecutionAttemptReceipt:
    schema_version: int
    commitment_sha256: str
    component_path: str
    component_blob_sha: str
    executor: str
    status: str
    failure_reason: str | None = None

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported execution attempt schema")
        object.__setattr__(self, "commitment_sha256", _hex("commitment_sha256", self.commitment_sha256, 64))
        object.__setattr__(self, "component_path", validate_repo_path(self.component_path))
        object.__setattr__(self, "component_blob_sha", _hex("component_blob_sha", self.component_blob_sha, 40))
        object.__setattr__(self, "executor", require_nonempty_text("executor", self.executor))
        if self.status not in _VALID_STATUS:
            raise ValueError("status must be SUCCEEDED/FAILED")
        if self.status == "FAILED":
            object.__setattr__(self, "failure_reason", require_nonempty_text("failure_reason", self.failure_reason))
        elif self.failure_reason is not None:
            raise ValueError("successful execution attempt cannot carry failure_reason")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_commitment(cls, commitment: ExecutionCommitment, *, status: str, failure_reason: str | None = None) -> "ExecutionAttemptReceipt":
        if not isinstance(commitment, ExecutionCommitment) or not commitment.accepted:
            raise ValueError("an accepted ExecutionCommitment is required")
        return cls(
            SCHEMA_VERSION, commitment.commitment_sha256, commitment.component_path,
            commitment.component_blob_sha, commitment.executor, status, failure_reason,
        )

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ExecutionAttemptReceipt":
        return cls(
            d["schema_version"], d["commitment_sha256"], d["component_path"], d["component_blob_sha"],
            d["executor"], d["status"], d.get("failure_reason"),
        )


def attempt_matches_commitment(commitment: ExecutionCommitment, attempt: ExecutionAttemptReceipt) -> bool:
    if not isinstance(commitment, ExecutionCommitment) or not isinstance(attempt, ExecutionAttemptReceipt):
        raise TypeError("commitment/attempt types invalid")
    return (
        commitment.accepted
        and attempt.commitment_sha256 == commitment.commitment_sha256
        and attempt.component_path == commitment.component_path
        and attempt.component_blob_sha == commitment.component_blob_sha
        and attempt.executor == commitment.executor
    )
