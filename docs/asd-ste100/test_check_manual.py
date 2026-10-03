"""Regression tests for the manual validator, without editing generated files."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_manual as manual


class ManualChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(manual.read(manual.DATA))
        cls.outputs = manual.render(cls.data)

    def test_source_coverage_detects_missing_block(self):
        data = copy.deepcopy(self.data)
        data["documents"][0]["blocks"].pop()
        errors = manual.validate(data, self.outputs)
        self.assertTrue(any("Source changed or coverage incomplete" in e for e in errors))

    def test_missing_identifier_and_value_fail(self):
        data = copy.deepcopy(self.data)
        block = data["documents"][0]["blocks"][4]
        block["en"] = block["en"].replace("takbox.local:8089:ssl", "wrong-host")
        errors = manual.validate(data, self.outputs)
        self.assertTrue(any("Missing identifiers" in e for e in errors))
        self.assertTrue(any("Missing numeric values" in e for e in errors))

    def test_generated_edit_is_stale(self):
        outputs = dict(self.outputs)
        file = manual.HERE / "en/index.md"
        outputs[file] += "\nUnexpected text.\n"
        self.assertTrue(any("stale" in e for e in manual.validate(self.data, outputs)))

    def test_invalid_local_anchor_fails(self):
        outputs = dict(self.outputs)
        file = manual.HERE / "en/index.md"
        outputs[file] += "\n[Broken](certificates-and-groups.md#missing-anchor)\n"
        self.assertTrue(any("Missing anchor" in e for e in manual.validate(self.data, outputs)))

    def test_condition_sentence_length_is_checked(self):
        findings = manual.procedure_lengths(Path("test.md"), "1. " + "word " * 21 + ".")
        self.assertEqual(len(findings), 1)
        self.assertEqual(manual.procedure_lengths(Path("test.md"), "1. Check " + chr(96) + "long command with many arguments" + chr(96) + "."), [])

    def test_task_links_resolve_to_translated_chapter(self):
        text = self.outputs[manual.HERE / "en/index.md"]
        self.assertIn("(certificates-and-groups.md#task-01)", text)
        self.assertIn("../../images/console-current-navbar.png", text)

    def test_table_cell_mismatch_fails(self):
        text = "| a | b |\n| --- | --- |\n| `x\\|y` | z |\n\n| a | b |\n| --- | --- |\n| 1 | 2 | 3 |\n"
        tables, errors = manual.table_errors(Path("test.md"), text)
        self.assertEqual(tables, 2)
        self.assertEqual(len(errors), 1)

    def test_comparison_tables_cover_every_block(self):
        tables = sum(
            manual.table_errors(p, t)[0] for p, t in self.outputs.items() if p.parent.name == "comparison"
        )
        self.assertEqual(tables, sum(len(d["blocks"]) for d in self.data["documents"]))

    def test_reports_use_lf(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(manual, "REPORTS", Path(directory)):
            manual.write_report("sample.json", {"a": 1})
            self.assertNotIn(b"\r\n", (Path(directory) / "sample.json").read_bytes())

    def test_plain_check_writes_no_reports(self):
        with mock.patch.object(sys, "argv", ["check_manual.py"]), \
                mock.patch.object(manual, "write_report") as write, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(manual.main(), 0)
        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
