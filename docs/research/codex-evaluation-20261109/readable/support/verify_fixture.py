"""Pre-experiment fixture checks only; never reads subject experiment outputs."""
import hashlib
import json
from pathlib import Path
import tempfile

import suite


support = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="repeatability-", dir=support) as temp:
    first = suite.build(Path(temp) / "first")
    second = suite.build(Path(temp) / "second")
    assert first == second, "build truth is not deterministic"
    assert suite._tree(Path(temp) / "first") == suite._tree(Path(temp) / "second")
    repeatability = {
        "same_input_bytes": True,
        "same_commit_sequence": True,
        "source_tree_sha": first["source_tree_sha"],
        "commit_sequence": first["task1_history"]["commit_sequence"],
    }

result = {
    "selfcheck": suite.selfcheck(),
    "repeatability": repeatability,
    "suite_sha256": hashlib.sha256((support / "suite.py").read_bytes()).hexdigest(),
}
(support / "fixture-verification.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
