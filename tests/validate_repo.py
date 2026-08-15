"""Repository-level validation for DIGR 3.0."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def require(cond, message):
    if not cond:
        errors.append(message)

version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

require(version == "3.0.0", "VERSION must be 3.0.0")
require(manifest.get("version") == version, "manifest version mismatch")
require(manifest.get("protocol") == "digr-v3.0", "protocol mismatch")

for path in manifest.get("core", []):
    require((ROOT / path).exists(), f"missing core file: {path}")

for path in [
    "entry/DEEP_ITERATION_ENTRY.md",
    "entry/HELP.md",
    "bootstrap/LOCAL_FALLBACK_CORE.md",
    "local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt",
    "runtime/clock_probe.py",
]:
    require((ROOT / path).exists(), f"missing required file: {path}")

require(not (ROOT / "runtime/reference_parser.py").exists(), "semantic parser must not be runtime authority")

active = "\n".join(
    p.read_text(encoding="utf-8")
    for p in [ROOT / "README.md", ROOT / "manifest.json", ROOT / "bootstrap/LOCAL_FALLBACK_CORE.md", *sorted((ROOT/"core").glob("*.md"))]
)
for banned in [
    "reference_model_effective_task_scale",
    "not_a_wall_clock_deadline",
    "t_is_not_a_hard_wall_clock_requirement",
]:
    require(banned not in active, f"legacy semantic-T token remains: {banned}")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("VALIDATION PASS")
