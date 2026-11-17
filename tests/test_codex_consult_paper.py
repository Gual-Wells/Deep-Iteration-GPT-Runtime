"""Synthetic contracts only; no model call or learner result."""
from pathlib import Path
import json
import tempfile
import unittest

from runtime import codex_paper as p
from runtime.codex_session import create_session
from tests.test_codex_paper import PdfWriter, PARAMETERS


@unittest.skipUnless(PdfWriter, "configured Python with pypdf required")
class ConsultPaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def fixture(self, version="0.10.0"):
        base = self.base / version
        base.mkdir()
        request = base / "request.txt"
        request.write_text("DIGRP(Light):synthetic contract fixture", encoding="utf-8")
        task = base / "task"
        pin = version + "@" + "a" * 40
        create_session(task, request=request, p_run=pin, visits_path=base / "visits", run_id=version)
        batch = base / "batch"
        index = p.initialize(batch, p_run=pin, authorization=request,
                             source_ref="synthetic-user", task_root=task)
        root = Path(p.add_paper(batch, paper_id="fixture", title="Synthetic",
                    line="M01", owner="native-Codex-fixture", parameters=PARAMETERS)["paper_root"])
        pdf = base / "source.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=210 * 72 / 25.4, height=297 * 72 / 25.4)
        with pdf.open("wb") as stream:
            writer.write(stream)
        p.register_source(root, {"id": "source", "path": str(pdf), "pages": 1,
                          "identity": "synthetic source"}, expected_revision=0, operation_id="source")
        mapping = {"parts": {part: "Natural chapter" for part in p.PARTS},
                   "assumptions": [], "claims": [], "chains": [], "experiments": [],
                   "coverage": [{"id": "body", "anchor": {"source": "source", "page": 1, "label": "body"},
                                 "location": "Natural chapter", "disposition": "explained"}]}
        md = base / "guide.md"
        md.write_text("## Natural chapter\nSynthetic content.\n\n## Local preparation\nSynthetic background.\n", encoding="utf-8")
        qa = base / "qa.json"
        qa.write_text(json.dumps({"pages": 1, "rendered_pages": 1, "formula_errors": [],
                                  "overflow": [], "missing_images": []}), encoding="utf-8")
        review = base / "review.md"
        review.write_text("Synthetic native review; not actual paper teaching or rendering evidence.", encoding="utf-8")
        payload = {"markdown": str(md), "pdfs": [str(pdf)], "qa": str(qa), "review": str(review),
                   "responsibility_report": {"N": 2, "R": 1, "D": 0, "V": 0}}
        return base, index, root, mapping, payload

    def test_integrated_functions_preserve_locations_and_require_real_public_file(self):
        base, index, root, mapping, payload = self.fixture()
        self.assertEqual(index["addon_version"], "0.4.0")
        mapping["mapping_contract"] = "integrated-functions-v1"
        mapping["parts"]["m4"] = ["Natural chapter", "Local preparation"]
        p.map_paper(root, mapping, expected_revision=1, operation_id="map")
        with self.assertRaisesRegex(ValueError, "actual Consult public"):
            p.prepare_candidate(root, payload, expected_revision=2, operation_id="missing-consult")
        guidance = base / "public.md"
        guidance.write_text("Synthetic explicit guidance: preserve this natural reading structure.\n", encoding="utf-8")
        payload["consultation"] = {"guidance": str(guidance), "source_ref": "synthetic-exchange",
                                   "scope": "Synthetic direction applies to this candidate; no provider claim."}
        p.prepare_candidate(root, payload, expected_revision=2, operation_id="candidate")
        before = (root / "paper.json").read_bytes()
        observed = p.inspect(root)
        self.assertEqual(observed["status"], "READY_LOCAL")
        self.assertEqual((root / "paper.json").read_bytes(), before)
        self.assertEqual(p._load(root)["candidate"]["addon_version"], "0.4.0")
        self.assertEqual(p._load(root)["candidate"]["responsibility_report"], payload["responsibility_report"])
        guidance.write_text("Changed synthetic guidance.\n", encoding="utf-8")
        self.assertEqual(p.inspect(root)["status"], "STALE_OR_UNAVAILABLE")

    def test_old_pin_keeps_its_addon_and_five_heading_contract(self):
        _, index, root, mapping, payload = self.fixture("0.9.0")
        self.assertEqual(index["addon_version"], "0.3.0")
        self.assertNotIn("consult_enabled", index)
        p.map_paper(root, mapping, expected_revision=1, operation_id="map")
        with self.assertRaisesRegex(ValueError, "reader order"):
            p.prepare_candidate(root, payload, expected_revision=2, operation_id="candidate")
        mapping["mapping_contract"] = "integrated-functions-v1"
        with self.assertRaisesRegex(ValueError, "paper 0.4"):
            p.map_paper(root, mapping, expected_revision=2, operation_id="new-contract-on-old-pin")


if __name__ == "__main__":
    unittest.main()
