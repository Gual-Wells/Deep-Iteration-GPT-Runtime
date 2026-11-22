from pathlib import Path
import json
import tempfile
import unittest

from runtime.codex_presets import resolve_defaults
from runtime.codex_profile import classify_invocation
from runtime.codex_session import create_line, create_session, line_packet, set_line_parameters


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

    def test_project_research_header_is_opt_in_and_versioned(self):
        current_pin = "1.4.0@" + "a" * 40
        old_pin = "1.3.0@" + "b" * 40
        fullwidth = "DIGR（Less，F（3），source=off）（X）：原任务：保留"
        current = classify_invocation(fullwidth, p_run=current_pin)
        self.assertEqual(current["classification"], "EXECUTING")
        self.assertEqual(current["task"], "原任务：保留")
        self.assertEqual(current["delivery_selection"]["mode"], "external")
        depth = current["depth_preferences"]
        self.assertEqual(depth["preference_baseline"]["F"], 0)
        self.assertEqual(depth["explicit_overrides"], {"F": 3})
        self.assertEqual(depth["unparsed_tokens"], ["source=off"])

        historical = classify_invocation(fullwidth, p_run=old_pin)["depth_preferences"]
        self.assertNotIn("F", historical["preference_baseline"])
        self.assertEqual(historical["explicit_overrides"], {})
        self.assertEqual(historical["unparsed_tokens"], ["F(3)", "source=off"])

        for surface, overrides in (("", {}), ("(F=0)", {"F": 0}), ("(F(2))", {"F": 2})):
            with self.subTest(surface=surface):
                result = classify_invocation(f"DIGR{surface}:task", p_run=current_pin)
                self.assertEqual(result["depth_preferences"]["explicit_overrides"], overrides)

    def test_project_research_rejects_malformed_or_conflicting_declarations(self):
        for surface in ("F=-1", "F(1.2)", "F()", "F=", "F=2,F(3)"):
            with self.subTest(surface=surface):
                result = classify_invocation(f"DIGR({surface}):task")
                self.assertEqual(result["classification"], "INVALID")
                self.assertIn("F", result["reason"])
        with self.assertRaisesRegex(ValueError, "F must be a nonnegative integer"):
            resolve_defaults(overrides={"F": True}, preference_only=True)

    def test_project_research_is_available_to_every_line_as_one_task_parameter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = root / "request.txt"
            request.write_text("DIGR(M=2,F=3,N=2):task", encoding="utf-8")
            arguments = {"request": request, "p_run": "1.4.0@" + "c" * 40}
            session = create_session(root / "task", **arguments)
            self.assertEqual(session["explicit_parameters"], {"F": 3, "M": 2, "N": 2})
            with self.assertRaisesRegex(ValueError, "conflicts with original header: F"):
                create_session(root / "conflict", **arguments, explicit_parameters={"F": 2})
            parameters = {"N": 2, "R": 0, "T": 0, "B": 0, "D": 0, "V": 0, "L": 3,
                          "S": {"n": 0, "t": 0, "r": 0, "b": 0}}
            for line_id in ("M01", "M02"):
                line = create_line(root / "task", line_id, parameters=parameters)
                self.assertEqual(line["explicit_parameter_differences"], [])
                self.assertNotIn("F", line["parameters"])
                self.assertIn('"F": 3', line_packet(root / "task", line_id))
            revised = set_line_parameters(root / "task", "M01", parameters={**parameters, "R": 1},
                                          reasons={"R": "Compare the whole design"})
            self.assertEqual(revised["explicit_parameter_differences"], [])
            self.assertEqual(revised["parameter_changes"][0]["changes"][0]["parameter"], "R")

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
