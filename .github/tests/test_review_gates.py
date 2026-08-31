"""Regression fixtures for the inline review and promotion-gate helpers."""

from pathlib import Path
import re
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "review.yml"
GATE_WORKFLOW = ROOT / ".github" / "workflows" / "promote-to-test.yml"
SHA = "0123456789abcdef0123456789abcdef01234567"

FIXTURES = {
    "legacy_incomplete": "\n".join(
        (
            "## Automated review",
            "",
            "_NOT reviewed - the wall-clock cap was reached: `.github/workflows/review.yml`._",
            f"<!-- airforce-review {SHA} -->",
        )
    ),
    "legacy_german_dropped": "\n".join(
        (
            "## Automatische Durchsicht",
            "_NICHT beurteilt, weil die Zeitkappe erreicht war: `review.yml`._",
            f"<!-- airforce-review {SHA} -->",
        )
    ),
    "legacy_english_invalid_json": "\n".join(
        (
            "> **The model answer was not usable JSON.** Findings may be missing.",
            f"<!-- airforce-review {SHA} -->",
        )
    ),
    "legacy_german_invalid_json": "\n".join(
        (
            "> **Die Modellantwort war kein verwertbares JSON.** Befunde koennen fehlen.",
            f"<!-- airforce-review {SHA} -->",
        )
    ),
    "new_incomplete": f"<!-- airforce-incomplete-review {SHA} -->",
    "english_high": "| 1 | `review.yml` | 930 | high | Incomplete runs look complete. |",
    "german_high": "| 1 | `review.yml` | 930 | hoch | Unvollstaendige Laeufe wirken fertig. |",
    "complete": "\n".join(
        (
            "## Automated review",
            "No findings.",
            "<!-- airforce-schwere hoch=0 mittel=0 -->",
            f"<!-- airforce-review {SHA} -->",
        )
    ),
    "push_complete": "\n".join(
        (
            "## Automatische Durchsicht (Direkt-Push)",
            "<!-- airforce-schwere hoch=0 mittel=0 -->",
            f"<!-- airforce-review-push {SHA} -->",
        )
    ),
}


def helper_namespace(path, block_name):
    """Execute one marked pure-helper block from an inline workflow script."""
    lines = path.read_text(encoding="utf-8").splitlines()
    begin = f"# BEGIN {block_name}"
    end = f"# END {block_name}"
    starts = [i for i, line in enumerate(lines) if line.strip() == begin]
    stops = [i for i, line in enumerate(lines) if line.strip() == end]
    if len(starts) != 1 or len(stops) != 1 or starts[0] >= stops[0]:
        raise AssertionError(f"Expected one ordered {block_name} helper block in {path}")
    source = textwrap.dedent("\n".join(lines[starts[0] + 1 : stops[0]]))
    namespace = {"re": re}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def inline_python(path):
    """Extract the one Python heredoc embedded in a workflow."""
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == "python3 - <<'PYEOF'"]
    stops = [i for i, line in enumerate(lines) if line.strip() == "PYEOF"]
    if len(starts) != 1 or len(stops) != 1 or starts[0] >= stops[0]:
        raise AssertionError(f"Expected one ordered Python heredoc in {path}")
    return textwrap.dedent("\n".join(lines[starts[0] + 1 : stops[0]]))


class ReviewGateFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviewer = helper_namespace(REVIEW_WORKFLOW, "REVIEW_MARKER_HELPERS")
        cls.gate = helper_namespace(GATE_WORKFLOW, "GATE_REVIEW_HELPERS")

    def test_legacy_incomplete_normal_markers_are_retryable_and_rejected(self):
        names = (
            "legacy_incomplete",
            "legacy_german_dropped",
            "legacy_english_invalid_json",
            "legacy_german_invalid_json",
        )
        for name in names:
            with self.subTest(fixture=name):
                body = FIXTURES[name]
                self.assertFalse(self.reviewer["review_is_complete"](body, SHA))
                self.assertFalse(self.gate["review_is_complete"](body, SHA))

    def test_new_incomplete_marker_is_not_complete(self):
        body = FIXTURES["new_incomplete"]
        self.assertNotIn("airforce-review", body)
        self.assertFalse(self.reviewer["review_is_complete"](body, SHA))
        self.assertFalse(self.gate["review_is_complete"](body, SHA))

    def test_complete_review_uses_the_exact_sha_marker(self):
        body = FIXTURES["complete"]
        self.assertTrue(self.reviewer["review_is_complete"](body, SHA))
        self.assertTrue(self.gate["review_is_complete"](body, SHA))
        self.assertFalse(self.gate["review_is_complete"](body, "f" * 40))
        self.assertFalse(
            self.gate["review_is_complete"]("## Automated review\nNo findings.", SHA)
        )

    def test_exact_push_marker_is_a_complete_gate_review(self):
        self.assertTrue(
            self.gate["review_is_complete"](FIXTURES["push_complete"], SHA)
        )

    def test_only_the_workflow_bot_can_satisfy_dedup_and_gate(self):
        bot_review = {
            "body": FIXTURES["complete"],
            "user": {"type": "Bot", "login": "github-actions[bot]"},
        }
        human_review = {
            "body": FIXTURES["complete"],
            "user": {"type": "User", "login": "reviewer"},
        }
        for helpers in (self.reviewer, self.gate):
            self.assertTrue(helpers["is_complete_bot_review"](bot_review, SHA))
            self.assertFalse(helpers["is_complete_bot_review"](human_review, SHA))

    def test_reviewer_emits_machine_readable_severity(self):
        findings = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "HIGH"},
            {"severity": "low"},
            {},
        ]
        self.assertEqual(
            self.reviewer["severity_marker"](findings),
            "<!-- airforce-schwere hoch=2 mittel=2 -->",
        )

    def test_english_high_is_counted(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["english_high"]), 1)

    def test_german_high_is_counted(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["german_high"]), 1)

    def test_complete_review_has_no_high_finding(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["complete"]), 0)

    def test_machine_marker_takes_precedence_over_legacy_table(self):
        body = "\n".join(
            ("<!-- airforce-schwere hoch=0 mittel=0 -->", FIXTURES["english_high"])
        )
        self.assertEqual(self.gate["high_finding_count"](body), 0)

    def test_legacy_notice_quoted_in_a_finding_does_not_make_review_incomplete(self):
        body = "\n".join(
            (
                "| 1 | `review.yml` | 1 | high | _NOT reviewed - the wall-clock cap was reached: |",
                f"<!-- airforce-review {SHA} -->",
            )
        )
        self.assertTrue(self.reviewer["review_is_complete"](body, SHA))
        self.assertTrue(self.gate["review_is_complete"](body, SHA))

    def test_sdk_review_gate_is_enabled(self):
        workflow = GATE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("DURCHSICHT_NOETIG: 'ja'", workflow)

    def test_changed_inline_python_scripts_compile(self):
        for workflow in (REVIEW_WORKFLOW, GATE_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                compile(inline_python(workflow), str(workflow), "exec")


if __name__ == "__main__":
    unittest.main()
