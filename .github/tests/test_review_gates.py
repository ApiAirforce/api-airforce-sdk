"""Regression fixtures for the inline review and promotion-gate helpers."""

import ast
from pathlib import Path
import json
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


def helper_namespace(path, block_name, initial=None):
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
    namespace.update(initial or {})
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
        cls.batches = helper_namespace(
            REVIEW_WORKFLOW,
            "REVIEW_BATCH_HELPERS",
            {
                "MAX_DIFF": 128,
                "json": json,
                "normalize_findings": cls.reviewer["normalize_findings"],
            },
        )
        cls.size = helper_namespace(REVIEW_WORKFLOW, "REVIEW_SIZE_HELPERS")

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

    def test_marker_must_occupy_an_exact_line(self):
        marker = f"<!-- airforce-review {SHA} -->"
        malformed = (
            marker + "suffix",
            "prefix" + marker,
            f"> {marker}",
        )
        for body in malformed:
            with self.subTest(body=body):
                self.assertFalse(self.reviewer["review_is_complete"](body, SHA))
                self.assertFalse(self.gate["review_is_complete"](body, SHA))
        self.assertTrue(self.reviewer["review_is_complete"](marker + "\r\n", SHA))
        self.assertTrue(self.gate["review_is_complete"](marker + "\r\n", SHA))

    def test_exact_push_marker_is_a_complete_gate_review(self):
        self.assertTrue(
            self.gate["review_is_complete"](FIXTURES["push_complete"], SHA)
        )

    def test_only_the_workflow_bot_can_satisfy_dedup_and_gate(self):
        bot_review = {
            "body": FIXTURES["complete"],
            "state": "COMMENTED",
            "user": {"type": "Bot", "login": "github-actions[bot]"},
        }
        human_review = {
            "body": FIXTURES["complete"],
            "state": "COMMENTED",
            "user": {"type": "User", "login": "reviewer"},
        }
        for helpers in (self.reviewer, self.gate):
            self.assertTrue(helpers["is_complete_bot_review"](bot_review, SHA))
            self.assertFalse(helpers["is_complete_bot_review"](human_review, SHA))

        bot_comment = {key: value for key, value in bot_review.items()
                       if key != "state"}
        self.assertTrue(self.gate["is_complete_bot_comment"](bot_comment, SHA))

    def test_only_submitted_pr_review_states_satisfy_dedup_and_gate(self):
        review = {
            "body": FIXTURES["complete"],
            "user": {"type": "Bot", "login": "github-actions[bot]"},
        }
        for state in ("PENDING", "DISMISSED", ""):
            review["state"] = state
            with self.subTest(state=state):
                self.assertFalse(
                    self.reviewer["is_complete_bot_review"](review, SHA)
                )
                self.assertFalse(self.gate["is_complete_bot_review"](review, SHA))
        for state in ("COMMENTED", "APPROVED", "CHANGES_REQUESTED"):
            review["state"] = state
            with self.subTest(state=state):
                self.assertTrue(
                    self.reviewer["is_complete_bot_review"](review, SHA)
                )
                self.assertTrue(self.gate["is_complete_bot_review"](review, SHA))

    def test_final_pr_head_covers_only_commits_from_a_normal_dev_merge(self):
        first_parent = "a" * 40
        earlier_commit = "b" * 40
        review_head = "c" * 40
        merge_sha = "d" * 40
        unrelated = "e" * 40
        candidate_shas = {earlier_commit, review_head, merge_sha}
        pull = {
            "merged_at": "2026-08-31T20:00:00Z",
            "merge_commit_sha": merge_sha,
            "base": {"ref": "dev"},
            "head": {"sha": review_head},
        }

        def normal_merge_git(*args):
            if args == ("rev-list", "--parents", "-1", merge_sha):
                return f"{merge_sha} {first_parent} {review_head}"
            if args == ("rev-list", f"{first_parent}..{review_head}"):
                return f"{review_head}\n{earlier_commit}"
            raise AssertionError(f"unexpected git call: {args!r}")

        prior_git = self.gate.get("git")
        self.gate["git"] = normal_merge_git
        try:
            fallback_head = self.gate["normal_merge_review_head"](
                pull, earlier_commit, candidate_shas
            )
            self.assertEqual(review_head, fallback_head)
            self.assertIsNone(self.gate["normal_merge_review_head"](
                pull, unrelated, candidate_shas
            ))

            for name, changed_pull, changed_candidates in (
                ("unmerged", dict(pull, merged_at=None), candidate_shas),
                (
                    "wrong base",
                    dict(pull, base={"ref": "main"}),
                    candidate_shas,
                ),
                ("outside candidate", pull, {earlier_commit, review_head}),
                (
                    "API head differs",
                    dict(pull, head={"sha": "f" * 40}),
                    candidate_shas,
                ),
            ):
                with self.subTest(case=name):
                    self.assertIsNone(self.gate["normal_merge_review_head"](
                        changed_pull, earlier_commit, changed_candidates
                    ))

            complete_at_head = FIXTURES["complete"].replace(SHA, review_head)
            review = {
                "body": complete_at_head,
                "commit_id": review_head,
                "user": {"type": "Bot", "login": "github-actions[bot]"},
            }
            for state in ("PENDING", "DISMISSED", "", None):
                review["state"] = state
                with self.subTest(state=state):
                    self.assertFalse(self.gate["is_complete_bot_review"](
                        review, fallback_head
                    ))
            review["state"] = "COMMENTED"
            self.assertTrue(self.gate["is_complete_bot_review"](
                review, fallback_head
            ))
        finally:
            if prior_git is None:
                self.gate.pop("git", None)
            else:
                self.gate["git"] = prior_git

    def test_squash_rebase_and_octopus_graphs_cannot_supply_fallback_evidence(self):
        first_parent = "a" * 40
        commit_sha = "b" * 40
        review_head = "c" * 40
        merge_sha = "d" * 40
        pull = {
            "merged_at": "2026-08-31T20:00:00Z",
            "merge_commit_sha": merge_sha,
            "base": {"ref": "dev"},
            "head": {"sha": review_head},
        }
        candidate_shas = {commit_sha, review_head, merge_sha}
        prior_git = self.gate.get("git")
        try:
            for name, parent_line in (
                ("squash or rebase", f"{merge_sha} {first_parent}"),
                (
                    "octopus",
                    f"{merge_sha} {first_parent} {review_head} {'e' * 40}",
                ),
            ):
                def graph_git(*args, line=parent_line):
                    if args == ("rev-list", "--parents", "-1", merge_sha):
                        return line
                    raise AssertionError(f"unexpected git call: {args!r}")

                self.gate["git"] = graph_git
                with self.subTest(case=name):
                    self.assertIsNone(self.gate["normal_merge_review_head"](
                        pull, commit_sha, candidate_shas
                    ))
        finally:
            if prior_git is None:
                self.gate.pop("git", None)
            else:
                self.gate["git"] = prior_git

    def test_exact_commit_evidence_precedes_pr_head_fallback_and_uses_head_answers(self):
        review_head = "c" * 40
        exact_high = {
            "body": "\n".join((
                FIXTURES["english_high"],
                f"<!-- airforce-review {SHA} -->",
            )),
            "created_at": "2026-08-31T20:00:00Z",
        }
        later_clean_fallback = {
            "body": FIXTURES["complete"].replace(SHA, review_head),
            "created_at": "2026-08-31T20:10:00Z",
            "review_head": review_head,
        }
        selected = self.gate["prefer_exact_review_evidence"](
            [exact_high], [later_clean_fallback]
        )
        self.assertEqual([exact_high], selected)
        self.assertEqual(
            1, self.gate["high_finding_count"](selected[0]["body"])
        )
        self.assertEqual(
            [], self.gate["response_comment_heads"](selected, SHA)
        )
        self.assertEqual(
            SHA, self.gate["review_response_sha"](selected[0], SHA)
        )
        all_findings = self.gate["latest_finding_evidence"](
            [exact_high], [later_clean_fallback]
        )
        self.assertEqual([exact_high, later_clean_fallback], all_findings)
        self.assertEqual(
            [1, 0],
            [self.gate["high_finding_count"](item["body"])
             for item in all_findings],
        )

        selected = self.gate["prefer_exact_review_evidence"](
            [], [later_clean_fallback]
        )
        self.assertEqual([later_clean_fallback], selected)
        self.assertEqual(
            [review_head], self.gate["response_comment_heads"](selected, SHA)
        )
        self.assertEqual(
            review_head,
            self.gate["review_response_sha"](selected[0], SHA),
        )
        commit_comment = {"body": "#erledigt exact"}
        pr_comment = {"body": "#erledigt PR"}
        head_comment = {"body": "#erledigt head"}
        self.assertEqual(
            [pr_comment, commit_comment],
            self.gate["response_comments_for_evidence"](
                exact_high,
                SHA,
                [commit_comment],
                [pr_comment],
                {review_head: [head_comment]},
            ),
        )
        self.assertEqual(
            [pr_comment, head_comment],
            self.gate["response_comments_for_evidence"](
                later_clean_fallback,
                SHA,
                [commit_comment],
                [pr_comment],
                {review_head: [head_comment]},
            ),
        )

        exact_clean = {
            "body": FIXTURES["complete"],
            "created_at": "2026-08-31T20:00:00Z",
        }
        fallback_high = dict(
            later_clean_fallback,
            body="\n".join((
                FIXTURES["english_high"],
                f"<!-- airforce-review {review_head} -->",
            )),
        )
        all_findings = self.gate["latest_finding_evidence"](
            [exact_clean], [fallback_high]
        )
        self.assertEqual(
            [0, 1],
            [self.gate["high_finding_count"](item["body"])
             for item in all_findings],
        )

        source = inline_python(GATE_WORKFLOW)
        self.assertRegex(
            source,
            r"(?s)for review_head in response_comment_heads\(fallback_found, sha\):.*?"
            r"head_comments\[review_head\] = paginated_gh\(\s*"
            r'"repos/%s/commits/%s/comments\?per_page=100"\s*'
            r"% \(REPO, review_head\)\)",
        )
        self.assertIn("and review_head != sha", source)

    def test_reviewer_emits_machine_readable_severity(self):
        findings = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "high"},
            {"severity": "low"},
            {"severity": "medium"},
        ]
        self.assertEqual(
            self.reviewer["severity_marker"](findings),
            "<!-- airforce-schwere hoch=2 mittel=2 -->",
        )

    def test_unknown_severity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported review severity"):
            self.reviewer["normalize_severity"]("critical")
        with self.assertRaisesRegex(ValueError, "unsupported review severity"):
            self.reviewer["severity_marker"]([{"severity": "critical"}])

        findings, invalid = self.reviewer["normalize_findings"](
            [{"path": "review.yml", "line": 1, "severity": "critical",
              "note": "unsupported level"}]
        )
        self.assertEqual(findings[0]["severity"], "high")
        self.assertTrue(invalid)

    def test_finding_severity_must_use_an_exact_schema_value(self):
        findings, invalid = self.reviewer["normalize_findings"](
            [{"path": "review.yml", "severity": " High ", "line": 1,
              "note": "noncanonical severity"}]
        )
        self.assertTrue(invalid)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertEqual(
            self.reviewer["severity_marker"](findings),
            "<!-- airforce-schwere hoch=1 mittel=0 -->",
        )

    def test_finding_schema_is_strict_for_local_and_global_results(self):
        normalize = self.reviewer["normalize_findings"]
        local = {
            "path": " leading-and-trailing ",
            "line": 7,
            "severity": "medium",
            "note": "local defect",
        }
        findings, invalid = normalize([local])
        self.assertFalse(invalid)
        self.assertEqual(local["path"], findings[0]["path"])

        malformed = (
            {"path": 7, "line": 1, "severity": "high", "note": "bad path"},
            {"path": " ", "line": 1, "severity": "high", "note": "bad path"},
            {"path": "x", "line": 1, "severity": "high", "note": 7},
            {"path": "x", "line": 1, "severity": "high", "note": "   "},
            {"path": "x", "line": "1", "severity": "high", "note": "bad"},
            {"path": "x", "line": True, "severity": "high", "note": "bad"},
            {"path": "x", "line": 0, "severity": "high", "note": "bad"},
        )
        for finding in malformed:
            with self.subTest(finding=finding):
                self.assertTrue(normalize([finding])[1])

        global_finding = {
            "path": "sdk/global.py",
            "severity": "high",
            "note": "cross-batch mismatch",
        }
        findings, invalid = normalize([global_finding], require_line=False)
        self.assertFalse(invalid)
        self.assertNotIn("line", findings[0])
        invalid_global = dict(global_finding, line="unknown")
        self.assertTrue(
            normalize([invalid_global], require_line=False)[1])

        missing_severity = dict(local)
        missing_severity.pop("severity")
        findings, invalid = normalize([missing_severity])
        self.assertTrue(invalid)
        self.assertEqual("high", findings[0]["severity"])

    def test_only_input_size_errors_trigger_resplitting(self):
        is_too_large = self.size["_ist_zu_gross"]
        positive = (
            "maximum context length exceeded",
            "input and output tokens exceed the context window",
            "too many input tokens",
            "prompt is too long",
            "payload exceeds the size limit",
            "request_too_large",
            "too many tokens",
            "max_tokens set, but request body exceeds the size limit",
        )
        negative = (
            "too large",
            "exceeds",
            "max_completion_tokens is too large",
            "max_tokens exceeds the supported output limit",
            "too many output tokens requested",
            "too many tokens per minute",
            "request exceeds rate limit",
            "response too large",
        )
        for message in positive:
            self.assertTrue(is_too_large(message), message)
        for message in negative:
            self.assertFalse(is_too_large(message), message)
        self.assertTrue(
            is_too_large("opaque relay error", "context_length_exceeded"))
        self.assertFalse(
            is_too_large("request too large", "rate_limit_error"))

        http_is_too_large = self.size["_http_ist_zu_gross"]
        self.assertTrue(http_is_too_large(413, "opaque relay error"))
        self.assertTrue(http_is_too_large(
            400, "input and output tokens exceed the context window"))
        self.assertFalse(http_is_too_large(
            429, "input exceeds the context window"))
        self.assertFalse(http_is_too_large(
            400, "max_completion_tokens requests too many tokens"))

        source = inline_python(REVIEW_WORKFLOW)
        size_check = source.index(
            'if _ist_zu_gross(str(e), getattr(e, "typ", "")):'
        )
        compatibility = source.index(
            'if getattr(e, "typ", "") == "invalid_request_error":'
        )
        self.assertLess(size_check, compatibility)
        self.assertRegex(
            source, r"_http_ist_zu_gross\(\s*e\.code, _leib,")
        self.assertNotIn("e.read()[:300]", source)
        self.assertIn("{_leib[:300]!r}", source)

    def test_english_high_is_counted(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["english_high"]), 1)

    def test_german_high_is_counted(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["german_high"]), 1)

    def test_complete_review_has_no_high_finding(self):
        self.assertEqual(self.gate["high_finding_count"](FIXTURES["complete"]), 0)

    def test_visible_high_cannot_be_hidden_by_machine_marker(self):
        body = "\n".join(
            ("<!-- airforce-schwere hoch=0 mittel=0 -->", FIXTURES["english_high"])
        )
        self.assertEqual(self.gate["high_finding_count"](body), 1)
        body = "\n".join(
            ("<!-- airforce-schwere hoch=0 mittel=0 -->", FIXTURES["german_high"])
        )
        self.assertEqual(self.gate["high_finding_count"](body), 1)

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

    def test_short_no_hunk_diff_is_preserved_verbatim(self):
        body = "diff --git a/old.txt b/new.txt\nsimilarity index 100%\n"
        self.assertEqual(
            self.batches["_split_file"]("new.txt", body, len(body)),
            [("new.txt", body)],
        )

    def test_oversized_no_hunk_diff_fails_closed(self):
        body = "diff --git a/old.txt b/new.txt\n" + ("metadata\n" * 40)
        with self.assertRaisesRegex(RuntimeError, "cannot be split"):
            self.batches["_split_file"]("new.txt", body, 64)
        with self.assertRaisesRegex(RuntimeError, "cannot be split"):
            self.batches["budget_batches"](body, 64)

    def test_oversized_unknown_diff_fails_closed(self):
        body = "unexpected diff payload\n" * 20
        with self.assertRaisesRegex(RuntimeError, "cannot be split"):
            self.batches["budget_batches"](body, 64)

    def test_long_stream_resplit_uses_actual_payload_size(self):
        first = ("diff --git a/one.rs b/one.rs\n--- a/one.rs\n+++ b/one.rs\n"
                 "@@ -0,0 +1 @@\n+" + "a" * 32_000 + "\n")
        second = ("diff --git a/two.rs b/two.rs\n--- a/two.rs\n+++ b/two.rs\n"
                  "@@ -0,0 +1 @@\n+" + "b" * 32_000 + "\n")
        raw = first + second
        initial = self.batches["budget_batches"](raw, 2_777_600)
        self.assertEqual(1, len(initial))
        limit, batches = self.batches["resplit_batch"](
            initial[0], 2_777_600
        )
        self.assertEqual(40_000, limit)
        self.assertEqual(2, len(batches))
        self.assertEqual(
            raw, "".join(body for batch in batches for _, body in batch)
        )

    def test_long_stream_resplit_rejects_no_progress(self):
        body = "diff --git a/blob.bin b/blob.bin\n" + ("metadata\n" * 5_000)
        parts = self.batches["budget_batches"](body, 2_777_600)[0]
        with self.assertRaisesRegex(RuntimeError, "cannot be split"):
            self.batches["resplit_batch"](parts, 2_777_600)

        original_budget = self.batches["budget_batches"]
        original_body = "".join(chunk for _, chunk in parts)
        self.batches["budget_batches"] = lambda _raw, _limit: [
            [("blob.bin", original_body)],
            [("blob.bin", "repeated diff header")],
        ]
        try:
            self.assertEqual(
                (None, []),
                self.batches["resplit_batch"](parts, 2_777_600),
            )
        finally:
            self.batches["budget_batches"] = original_budget

        source = inline_python(REVIEW_WORKFLOW)
        self.assertIn(
            "smaller retry is possible - marking it incomplete", source
        )
        self.assertIn("dropped += dropped_paths(teile)", source)

    def test_git_paths_come_from_authoritative_metadata(self):
        cases = (
            (
                "diff --git a/foo b/bar.txt b/foo b/bar.txt\n"
                "--- a/foo b/bar.txt\n+++ b/foo b/bar.txt\n"
                "@@ -1 +1 @@\n-old\n+new\n",
                "foo b/bar.txt",
            ),
            (
                "diff --git a/ leading.txt b/ leading.txt\n"
                "--- a/ leading.txt\t\n+++ b/ leading.txt\t\n"
                "@@ -1 +1 @@\n-old\n+new\n",
                " leading.txt",
            ),
            (
                "diff --git a/trailing.txt  b/trailing.txt \n"
                "--- a/trailing.txt \t\n+++ b/trailing.txt \t\n"
                "@@ -1 +1 @@\n-old\n+new\n",
                "trailing.txt ",
            ),
            (
                'diff --git "a/docs/a\\tb.txt" "b/docs/a\\tb.txt"\n'
                '--- "a/docs/a\\tb.txt"\n+++ "b/docs/a\\tb.txt"\n'
                "@@ -1 +1 @@\n-old\n+new\n",
                "docs/a\tb.txt",
            ),
            (
                'diff --git "a/Gr\\303\\274\\303\\237e.txt" '
                '"b/Gr\\303\\274\\303\\237e.txt"\n'
                '--- "a/Gr\\303\\274\\303\\237e.txt"\n'
                '+++ "b/Gr\\303\\274\\303\\237e.txt"\n'
                "@@ -1 +1 @@\n-old\n+new\n",
                "Grüße.txt",
            ),
            (
                'diff --git "a/docs/a\\\"b.md" "b/docs/a\\\"b.md"\n'
                '--- "a/docs/a\\\"b.md"\n+++ "b/docs/a\\\"b.md"\n'
                "@@ -1 +1 @@\n-old\n+new\n",
                'docs/a"b.md',
            ),
            (
                'diff --git "a/docs/a\\\\b.md" "b/docs/a\\\\b.md"\n'
                '--- "a/docs/a\\\\b.md"\n+++ "b/docs/a\\\\b.md"\n'
                "@@ -1 +1 @@\n-old\n+new\n",
                "docs/a\\b.md",
            ),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, self.batches["diff_target_path"](raw))
                paths = [path for batch in self.batches["budget_batches"](raw, 512)
                         for path, _ in batch]
                self.assertEqual([expected], paths)

    def test_hunk_content_cannot_override_file_metadata(self):
        raw = (
            "diff --git a/real.rs b/real.rs\n"
            "--- a/real.rs\n+++ b/real.rs\n"
            "@@ -1 +1 @@\n--- a/fake.rs\n+++ b/fake.rs\n"
        )
        self.assertEqual("real.rs", self.batches["diff_target_path"](raw))

    def test_add_delete_rename_and_copy_paths_remain_identified(self):
        cases = (
            (
                "diff --git a/new file b/new file\n--- /dev/null\n"
                "+++ b/new file\n@@ -0,0 +1 @@\n+new\n",
                "new file",
            ),
            (
                "diff --git a/old file b/old file\n--- a/old file\n"
                "+++ /dev/null\n@@ -1 +0,0 @@\n-old\n",
                "old file",
            ),
            (
                "diff --git a/old b/new name\nsimilarity index 100%\n"
                "rename from old\nrename to new name\n",
                "new name",
            ),
            (
                "diff --git a/old b/copied name\nsimilarity index 100%\n"
                "copy from old\ncopy to copied name\n",
                "copied name",
            ),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, self.batches["diff_target_path"](raw))
                self.assertEqual(expected, self.batches["diff_chunks"](raw)[0][0])

    def test_file_diffs_are_grouped_whole_before_path_parsing(self):
        first = (
            "diff --git a/one.rs b/one.rs\n--- a/one.rs\n+++ b/one.rs\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        second = (
            "diff --git a/two.rs b/two.rs\n--- a/two.rs\n+++ b/two.rs\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        chunks = self.batches["diff_chunks"](first + second)
        self.assertEqual(["one.rs", "two.rs"], [path for path, _ in chunks])
        self.assertEqual([first, second], [body for _, body in chunks])

    def test_binary_mode_only_and_unknown_paths_use_a_sentinel(self):
        binary = (
            "diff --git a/image.bin b/image.bin\n"
            "Binary files a/image.bin and b/image.bin differ\n"
        )
        mode_only = (
            "diff --git a/run.sh b/run.sh\nold mode 100644\nnew mode 100755\n"
        )
        empty_file = (
            "diff --git a/empty.txt b/empty.txt\nnew file mode 100644\n"
            "index 0000000..e69de29\n"
        )
        ambiguous_header = (
            "diff --git a/dir b/file b/dir b/file\n"
            "similarity index 100%\n"
        )
        sentinel = self.batches["UNKNOWN_PATH"]
        for body in (binary, mode_only, empty_file, ambiguous_header):
            with self.subTest(body=body.splitlines()[1]):
                self.assertEqual(sentinel, self.batches["diff_target_path"](body))
                self.assertEqual([(sentinel, body)], self.batches["diff_chunks"](body))
                rebuilt = "".join(
                    chunk for batch in self.batches["budget_batches"](body, 512)
                    for _, chunk in batch
                )
                self.assertEqual(body, rebuilt)
                self.assertEqual(
                    [sentinel], self.batches["changed_path_manifest"](body)
                )
        self.assertEqual(
            [sentinel], self.batches["dropped_paths"]([(None, binary)])
        )

    def test_malformed_git_markers_fail_closed(self):
        for marker in ('+++ "b/missing', "+++ c/x", '+++ "b/x" unexpected'):
            with self.subTest(marker=marker):
                with self.assertRaises(ValueError):
                    self.batches["diff_marker_path"](marker, "b/")

    def test_paginated_review_sources_are_flattened_without_loss(self):
        pages = [[{"id": 1}], [{"id": 2}], []]
        self.assertEqual(
            [{"id": 1}, {"id": 2}],
            self.reviewer["flatten_paginated_lists"](pages),
        )
        self.assertEqual(
            [{"id": 1}, {"id": 2}],
            self.gate["flatten_paginated_lists"](pages),
        )
        for helpers in (self.reviewer, self.gate):
            with self.assertRaises(ValueError):
                helpers["flatten_paginated_lists"]([[{"id": 1}], {"id": 2}])

    def test_api_pagination_and_fail_closed_reads_are_wired(self):
        calls = []

        def fake_review_gh(path, *extra):
            calls.append((path, extra))
            return [[{"id": 1}], [{"id": 2}]]

        self.reviewer["gh"] = fake_review_gh
        self.assertEqual(
            [{"id": 1}, {"id": 2}],
            self.reviewer["gh_paginated_list"]("repos/o/r/pulls/1/reviews"),
        )
        self.assertEqual(("--paginate", "--slurp"), calls[-1][1])

        def fake_gate_gh(path, *extra, **options):
            calls.append((path, extra, options))
            return [[{"id": 1}], [{"id": 2}]]

        self.gate["gh_json"] = fake_gate_gh
        self.assertEqual(
            [{"id": 1}, {"id": 2}],
            self.gate["paginated_gh"]("repos/o/r/commits/s/comments"),
        )
        self.assertEqual(("--paginate", "--slurp"), calls[-1][1])
        self.assertTrue(calls[-1][2]["loud"])

        self.gate["gh_json"] = lambda *args, **kwargs: None
        with self.assertRaises(RuntimeError):
            self.gate["paginated_gh"]("repos/o/r/commits/s/comments")
        with self.assertRaises(RuntimeError):
            self.gate["required_gh_json"]("repos/o/r/collaborators/u/permission")

    def test_every_review_source_uses_fail_closed_pagination(self):
        source = inline_python(GATE_WORKFLOW)
        endpoints = (
            "commits/%s/pulls?per_page=100",
            "commits/%s/comments?per_page=100",
            "pulls/%s/reviews?per_page=100",
            "issues/%s/comments?per_page=100",
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                self.assertIn(endpoint, source)
        self.assertGreaterEqual(source.count("paginated_gh("), 6)
        self.assertNotIn(
            'gh_json("repos/%s/commits/%s/comments?per_page=100"', source
        )

    def test_reconciliation_envelope_and_exact_coverage_are_fail_closed(self):
        paths = ["sdk/a.py", "sdk/b.py"]
        reports = [
            self.batches["make_batch_report"](
                "batch-1", [paths[0]], "producer changed",
                ["response field renamed"], [],
            ),
            self.batches["make_batch_report"](
                "batch-2", [paths[1]], "consumer changed",
                ["client reads response field"], [],
            ),
        ]
        self.assertTrue(self.batches["reports_cover_manifest"](paths, reports))
        prompt = self.batches["reconciliation_text"](paths, reports)
        envelope = json.loads(prompt.split("\n\n", 1)[1])
        self.assertEqual(paths, envelope["changed_paths"])
        self.assertEqual(reports, envelope["batch_reports"])

        valid = json.dumps(
            {
                "verdict": "findings",
                "summary": "producer and consumer disagree",
                "cross_batch_facts": [],
                "findings": [
                    {
                        "path": "sdk/b.py",
                        "severity": "high",
                        "note": "consumer still uses the old field",
                    }
                ],
                "covered_batches": ["batch-2", "batch-1"],
                "covered_paths": [paths[1], paths[0]],
            }
        )
        summary, findings, broken = self.batches[
            "parse_reconciliation_response"
        ](valid, ["batch-1", "batch-2"], paths)
        self.assertFalse(broken)
        self.assertIn("disagree", summary)
        self.assertNotIn("line", findings[0])

        for field, value in (
            ("covered_batches", ["batch-1"]),
            ("covered_batches", ["batch-1", "batch-2", "batch-2"]),
            ("covered_paths", [paths[0]]),
            ("covered_paths", paths + ["extra.py"]),
        ):
            payload = json.loads(valid)
            payload[field] = value
            with self.subTest(field=field, value=value):
                self.assertTrue(
                    self.batches["parse_reconciliation_response"](
                        json.dumps(payload), ["batch-1", "batch-2"], paths
                    )[2]
                )

    def test_reconciliation_keeps_valid_findings_across_sibling_errors(self):
        batch_ids = ["batch-1", "batch-2"]
        paths = ["sdk/a.py", "sdk/b.py"]
        valid_high = {
            "path": paths[1],
            "severity": "high",
            "note": "consumer still uses the old field",
        }
        base = {
            "verdict": "findings",
            "summary": "producer and consumer disagree",
            "cross_batch_facts": ["the response field changed"],
            "findings": [valid_high],
            "covered_batches": batch_ids,
            "covered_paths": paths,
        }

        def changed(mutator):
            payload = json.loads(json.dumps(base))
            mutator(payload)
            return payload

        cases = [
            ("missing-verdict", changed(lambda value: value.pop("verdict")), 1),
            ("wrong-verdict", changed(
                lambda value: value.__setitem__("verdict", "unknown")), 1),
            ("missing-summary", changed(lambda value: value.pop("summary")), 1),
            ("wrong-summary-type", changed(
                lambda value: value.__setitem__("summary", {})), 1),
            ("wrong-cross-batch-facts", changed(
                lambda value: value.__setitem__("cross_batch_facts", {})), 1),
            ("invalid-second-finding", changed(
                lambda value: value["findings"].append({
                    "path": paths[0], "severity": "medium"
                })), 1),
            ("missing-batch-coverage", changed(
                lambda value: value.pop("covered_batches")), 1),
            ("missing-path-coverage", changed(
                lambda value: value.pop("covered_paths")), 1),
            ("inexact-batch-coverage", changed(
                lambda value: value.__setitem__(
                    "covered_batches", [batch_ids[0]])), 1),
            ("inexact-path-coverage", changed(
                lambda value: value.__setitem__(
                    "covered_paths", [paths[0], "sdk/extra.py"])), 1),
            ("duplicate-batch-coverage", changed(
                lambda value: value.__setitem__(
                    "covered_batches", batch_ids + [batch_ids[1]])), 1),
            ("duplicate-path-coverage", changed(
                lambda value: value.__setitem__(
                    "covered_paths", paths + [paths[1]])), 1),
            ("unknown-severity", changed(
                lambda value: value["findings"].append({
                    "path": paths[0],
                    "severity": "critical",
                    "note": "a second conservative finding",
                })), 2),
        ]

        parse = self.batches["parse_reconciliation_response"]
        for name, payload, expected_count in cases:
            with self.subTest(case=name):
                _, findings, broken = parse(
                    json.dumps(payload), batch_ids, paths)
                self.assertTrue(broken)
                self.assertEqual(valid_high, findings[0])
                self.assertEqual(expected_count, len(findings))
                self.assertTrue(all(
                    finding["severity"] == "high" for finding in findings
                ))

    def test_review_envelopes_require_every_top_level_schema_field(self):
        validate = self.batches["review_envelope_is_valid"]
        valid = {
            "verdict": "lgtm",
            "summary": "",
            "cross_batch_facts": [],
            "findings": [],
        }
        self.assertTrue(validate(valid))
        for field in ("summary", "cross_batch_facts", "findings"):
            malformed = dict(valid)
            malformed.pop(field)
            with self.subTest(missing=field):
                self.assertFalse(validate(malformed))

        invalid_values = {
            "summary": ({}, [], 0, False, None),
            "cross_batch_facts": ({}, "", 0, False, None, [1], ["   "]),
            "findings": ({}, "", 0, False, None),
        }
        for field, values in invalid_values.items():
            for value in values:
                malformed = dict(valid)
                malformed[field] = value
                with self.subTest(field=field, value=value):
                    self.assertFalse(validate(malformed))

        self.assertFalse(validate(dict(
            valid, verdict="findings", findings=[]
        )))
        # Keep the existing minimal contract: empty summaries and lgtm findings
        # remain valid; this fix only closes missing or malformed fields.
        self.assertTrue(validate(dict(
            valid,
            findings=[{"path": "sdk/a.py", "line": 1,
                       "severity": "low", "note": "visible"}],
        )))

        source = inline_python(REVIEW_WORKFLOW)
        self.assertGreaterEqual(
            source.count("review_envelope_is_valid(verdict)"), 2
        )

    def test_global_findings_are_body_only_and_local_lines_stay_inline(self):
        local = [
            {
                "path": "sdk/a.py",
                "line": 42,
                "severity": "medium",
                "note": "local defect",
            }
        ]
        global_findings = [
            {
                "path": "sdk/b.py",
                "line": 999,
                "severity": "high",
                "note": "cross-batch mismatch",
            }
        ]
        body_only = self.batches["body_only_findings"](global_findings)
        self.assertEqual(42, local[0]["line"])
        self.assertEqual(999, global_findings[0]["line"])
        self.assertNotIn("line", body_only[0])

        source = inline_python(REVIEW_WORKFLOW)
        self.assertIn("findings += f", source)
        self.assertIn("findings += body_only_findings(global_findings)", source)
        tree = ast.parse(source)
        guards = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If) and ast.unparse(node.test) == "not broken"
        ]
        finding_merges = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.AugAssign)
            and ast.unparse(node.value) == "body_only_findings(global_findings)"
        ]
        self.assertEqual(1, len(guards))
        self.assertEqual(1, len(finding_merges))
        self.assertLess(guards[0].end_lineno, finding_merges[0].lineno)
        self.assertNotIn(finding_merges[0], list(ast.walk(guards[0])))

        reconciliation_bindings = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name)
                    and target.id == "reconciliation_failed"
                    for target in node.targets)
            and ast.unparse(node.value) == "broken"
        ]
        incomplete_bindings = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "incomplete"
                    for target in node.targets)
        ]
        marker_bindings = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "marker"
                    for target in node.targets)
        ]
        failing_guards = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and "reconciliation_failed" in ast.unparse(node.test)
            and any(
                isinstance(child, ast.Call)
                and ast.unparse(child.func) == "sys.exit"
                and len(child.args) == 1
                and isinstance(child.args[0], ast.Constant)
                and child.args[0].value == 1
                for child in ast.walk(node)
            )
        ]
        self.assertEqual(1, len(reconciliation_bindings))
        self.assertEqual(1, len(incomplete_bindings))
        self.assertEqual(1, len(marker_bindings))
        self.assertEqual(1, len(failing_guards))
        self.assertEqual(
            "parse_kaputt or bool(dropped) or reconciliation_failed",
            ast.unparse(incomplete_bindings[0].value),
        )
        self.assertEqual(
            "incomplete_review_marker(head) if incomplete else "
            "complete_review_marker(head)",
            ast.unparse(marker_bindings[0].value),
        )
        self.assertLess(
            reconciliation_bindings[0].lineno, finding_merges[0].lineno)
        self.assertLess(incomplete_bindings[0].lineno, marker_bindings[0].lineno)
        self.assertLess(marker_bindings[0].lineno, failing_guards[0].lineno)

    def test_global_prompt_never_requests_or_guesses_line_numbers(self):
        source = inline_python(REVIEW_WORKFLOW)
        start = source.index("reconciliation_system = (")
        stop = source.index("def stapel_text", start)
        prompt = source[start:stop]
        self.assertIn('"findings":[{"path":"...",', prompt)
        self.assertIn('"cross_batch_facts":[]', prompt)
        self.assertNotIn('"line":', prompt)
        self.assertIn("never include or guess line numbers", prompt)
        self.assertIn('"cross_batch_facts":["..."]', source)
        self.assertIn(
            "if (len(batch_reports) > 1 and not parse_kaputt and not dropped",
            source,
        )

    def test_changed_inline_python_scripts_compile(self):
        for workflow in (REVIEW_WORKFLOW, GATE_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                compile(inline_python(workflow), str(workflow), "exec")

    def test_gate_window_listing_fails_closed_on_untrusted_git_metadata(self):
        # Review findings on sdk#64 (backend#548): the author name and the
        # subject are contributor-controlled, so neither may decide whether a
        # commit is checked. Records are NUL-delimited, a record that still
        # does not parse counts as unreviewed, and the bot exemption comes
        # from GitHub's account type, not from `%an`.
        source = inline_python(GATE_WORKFLOW)
        self.assertIn('"-z",', source)
        self.assertIn("without.extend(malformed)", source)
        self.assertIn("def commit_is_trusted_bot(sha):", source)
        self.assertIn('author.get("type") == "Bot"', source)
        self.assertIn("if commit_is_trusted_bot(sha):", source)
        self.assertNotIn('author.endswith("[bot]")', source)
        self.assertNotIn('author in ("github-actions", "dependabot")', source)
        # A malformed record without a SHA holds the whole gate.
        self.assertIn("The commit list could not be read.", source)
        self.assertLess(source.index("without.extend(malformed)"),
                        source.index("for sha, author, subject in entries:"))


if __name__ == "__main__":
    unittest.main()
