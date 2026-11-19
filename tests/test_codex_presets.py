from pathlib import Path
import json
import tempfile
import unittest

from runtime.codex_presets import resolve_defaults
from runtime.codex_profile import classify_invocation
from runtime.codex_session import create_session


class CodexPresetModeTests(unittest.TestCase):
    def test_named_values_override_tier_without_changing_route_or_task(self):
        text = "DIGRC（Less，N（8），S（n（3），t（20min）））（X）：保留：原任务\n"
        result = classify_invocation(text)
        self.assertEqual(result["classification"], "EXECUTING")
        self.assertEqual(result["task"], "保留：原任务\n")
        self.assertEqual(result["invocation_key"], "DIGRC")
        self.assertTrue(result["consult_selection"])
        depth = result["depth_preferences"]
        self.assertEqual((depth["preference_baseline"]["N"], depth["preference_baseline"]["R"]), (6, 2))
        self.assertEqual(depth["explicit_overrides"], {"N": 8, "S": {"n": 3, "t": "20min"}})
        self.assertEqual(result["delivery_selection"]["mode"], "external")

    def test_light_is_managed_and_never_reduces_native_isolation(self):
        result = classify_invocation("DIGR(Light):small actual task")
        self.assertEqual(result["classification"], "EXECUTING")
        self.assertFalse(result["consult_selection"])
        self.assertEqual(resolve_defaults("(Light)")["parameters"],
                         resolve_defaults("(standard)")["parameters"])
        with self.assertRaisesRegex(ValueError, "native L3"):
            resolve_defaults("(Less,L=2)")

    def test_conflicting_presets_are_rejected_and_positional_text_is_retained(self):
        self.assertEqual(classify_invocation("DIGR(Less,More):task")["classification"], "INVALID")
        with self.assertRaisesRegex(ValueError, "unknown"):
            resolve_defaults("(preset=Typo)")
        self.assertEqual(resolve_defaults("(12,60min,4)")["unparsed_tokens"],
                         ["12", "60min", "4"])

    def test_longest_alias_does_not_capture_words_or_quotes(self):
        for text in ("DIGRConsultation:word", "DIGRProblem:word", "digrC:task", "'DIGRC:quote'"):
            self.assertEqual(classify_invocation(text)["classification"], "NATIVE")
        self.assertEqual(classify_invocation("DIGRC/help")["classification"], "HELP")

    def test_historical_sessions_freeze_mode_and_explicit_tier_but_old_paper_stays_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = root / "request.txt"
            request.write_text("DIGRC(Less,N=9):real task", encoding="utf-8")
            new = create_session(root / "new", request=request, p_run="0.10.0@" + "a" * 40,
                                 visits_path=root / "visits", run_id="new")
            self.assertEqual(new["execution_profile"]["mode"], "CONSULT")
            self.assertEqual((new["explicit_parameters"]["N"], new["explicit_parameters"]["R"]), (9, 2))
            with self.assertRaisesRegex(ValueError, "0.10"):
                create_session(root / "bad", request=request, p_run="0.9.0@" + "b" * 40,
                               visits_path=root / "visits", run_id="bad")
            request.write_text("DIGRP:old paper task", encoding="utf-8")
            old = create_session(root / "old", request=request, p_run="0.9.0@" + "b" * 40,
                                 visits_path=root / "visits", run_id="old")
            self.assertNotIn("execution_profile", old)
            request.write_text("DIGR:unchanged native task", encoding="utf-8")
            native = create_session(root / "native", request=request, p_run="0.10.0@" + "a" * 40,
                                    visits_path=root / "visits", run_id="native")
            self.assertEqual(native["execution_profile"]["mode"], "NATIVE")
            self.assertEqual(native["explicit_parameters"], {})


if __name__ == "__main__":
    unittest.main()
