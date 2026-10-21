"""Synthetic controls for the review client's requested service tier.

Every test runs the workflows' own inline code. A loopback server stands in for
the relay, so no model, relay or network outside this host is contacted.
"""

import ast
import contextlib
import http.server
import io
import json
import os
import re
import sys
import textwrap
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (ROOT / ".github" / "workflows" / "review.yml",)
REQUEST_CODE = {"_RelayFehler", "_StromUnbrauchbar", "_relay_fehler", "_stroemen", "call"}
REQUEST_CONSTANTS = frozenset()
SIZE_CODE = {"_ist_zu_gross", "_http_ist_zu_gross"}
SIZE_CONSTANTS = {"ABRISS_IST_GROESSE"}


def module_nodes(path):
    source = path.read_text(encoding="utf-8")
    match = re.search(r"python3 - <<'PYEOF'\r?\n(.*?)\r?\n\s+PYEOF", source, re.S)
    if not match:
        raise AssertionError(f"embedded Python not found in {path}")
    return ast.parse(textwrap.dedent(match.group(1)), filename=str(path)).body


def assigned_names(node):
    names = set()
    for target in getattr(node, "targets", []):
        for name in ast.walk(target):
            if isinstance(name, ast.Name):
                names.add(name.id)
    return names


def selected_namespace(path, functions, constants=frozenset(), **extra):
    selected = [node for node in module_nodes(path)
                if (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in functions)
                or (isinstance(node, ast.Assign) and assigned_names(node) & set(constants))]
    namespace = {"json": json, "re": re, "sys": sys, "time": time, "urllib": urllib}
    namespace.update(extra)
    exec(compile(ast.Module(selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def config_nodes(path):
    """The tier setting, its validation and the report lists, in source order."""
    return [node for node in module_nodes(path)
            if (isinstance(node, ast.Assign)
                and assigned_names(node) & {"SERVICE_TIER", "KNOWN_TIERS"})
            or (isinstance(node, ast.If)
                and ast.unparse(node.test) == "SERVICE_TIER is None")]


def load_config(path, value):
    env = {key: val for key, val in os.environ.items() if key != "SERVICE_TIER"}
    if value is not None:
        env["SERVICE_TIER"] = value
    namespace = {"os": os, "sys": sys}
    with mock.patch.dict(os.environ, env, clear=True):
        exec(compile(ast.Module(config_nodes(path), type_ignores=[]), str(path), "exec"),
             namespace)
    return namespace


def batch_function(path):
    return next(node for node in module_nodes(path)
                if isinstance(node, ast.FunctionDef) and node.name == "durchsicht")


def observed_tier_statements(path):
    body = list(ast.walk(batch_function(path)))
    assign = next(node for node in body if isinstance(node, ast.Assign)
                  and assigned_names(node) == {"_tier"})
    record = next(node for node in body if isinstance(node, ast.Expr)
                  and ast.unparse(node).startswith("OBSERVED_TIERS.append("))
    return [assign, record]


def footer_statement(path):
    return next(node for node in module_nodes(path)
                if isinstance(node, ast.AugAssign) and "api.airforce" in ast.unparse(node))


def sse(*chunks, done=True):
    events = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
    if done:
        events.append("data: [DONE]\n\n")
    return 200, "text/event-stream", "".join(events)


def delta(text, tier=None):
    chunk = {"choices": [{"delta": {"content": text}}]}
    if tier is not None:
        chunk["service_tier"] = tier
    return chunk


def rejected_tier():
    return 400, "application/json", json.dumps({"error": {
        "message": "Unsupported value: service_tier", "type": "invalid_request_error",
        "param": "service_tier"}})


class Relay:
    """Loopback relay: records every request body and replays scripted answers."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []
        relay = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                relay.requests.append(json.loads(self.rfile.read(length)))
                status, content_type, body = relay.answers.pop(0)
                payload = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def payload(tier="priority"):
    body = {"model": "fixture", "reasoning_effort": "xhigh",
            "messages": [{"role": "user", "content": "INPUT"}]}
    if tier:
        body["service_tier"] = tier
    return body


class ServiceTierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The loopback relay must never be reached through a configured proxy.
        cls.opener = urllib.request._opener
        urllib.request.install_opener(
            urllib.request.build_opener(urllib.request.ProxyHandler({})))

    @classmethod
    def tearDownClass(cls):
        urllib.request._opener = cls.opener

    def call(self, workflow, answers, body):
        with Relay(answers) as relay, contextlib.redirect_stderr(io.StringIO()):
            namespace = selected_namespace(workflow, REQUEST_CODE, REQUEST_CONSTANTS,
                                           BASE=relay.base, KEY="synthetic-key")
            try:
                return namespace["call"](body), relay.requests
            except urllib.error.HTTPError as error:
                return error, relay.requests

    def test_setting_defaults_to_priority_and_accepts_only_known_spellings(self):
        for workflow in WORKFLOWS:
            for value, expected in ((None, "priority"), ("", "priority"),
                                    ("priority", "priority"), (" Fast ", "fast"),
                                    ("none", ""), ("OFF", "")):
                with self.subTest(workflow=workflow.name, value=value):
                    config = load_config(workflow, value)
                    self.assertEqual(expected, config["SERVICE_TIER"])
                    self.assertEqual([], config["OBSERVED_TIERS"])
            with self.subTest(workflow=workflow.name, value="turbo"):
                with self.assertRaises(SystemExit) as stop:
                    load_config(workflow, "turbo")
                self.assertIn("PULLFROG_SERVICE_TIER", str(stop.exception.code))

    def test_invalid_setting_stops_before_any_request_code_exists(self):
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                nodes = module_nodes(workflow)
                check = next(i for i, node in enumerate(nodes)
                             if isinstance(node, ast.If)
                             and ast.unparse(node.test) == "SERVICE_TIER is None")
                first_function = next(i for i, node in enumerate(nodes)
                                      if isinstance(node, ast.FunctionDef))
                self.assertLess(check, first_function)

    def test_streamed_request_carries_the_tier_and_returns_the_answered_one(self):
        for workflow in WORKFLOWS:
            for answered in ("priority", "default", None):
                with self.subTest(workflow=workflow.name, answered=answered):
                    out, requests = self.call(
                        workflow, [sse(delta("o", answered), delta("k"))], payload())
                    self.assertEqual(1, len(requests))
                    self.assertEqual("priority", requests[0]["service_tier"])
                    self.assertTrue(requests[0]["stream"])
                    self.assertEqual("ok", out["choices"][0]["message"]["content"])
                    self.assertEqual(answered, out["service_tier"])

    def test_json_answer_to_a_streamed_request_keeps_its_tier(self):
        whole = json.dumps({"choices": [{"message": {"content": "ok"}}],
                            "service_tier": "priority"})
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                out, requests = self.call(
                    workflow, [(200, "application/json", whole)], payload())
                self.assertEqual(1, len(requests))
                self.assertEqual("priority", out["service_tier"])

    def test_non_streaming_fallback_sends_and_reads_the_tier(self):
        whole = json.dumps({"choices": [{"message": {"content": "ok"}}],
                            "service_tier": "default"})
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                out, requests = self.call(
                    workflow, [sse(delta("partial"), done=False),
                               (200, "application/json", whole)], payload("fast"))
                self.assertEqual(2, len(requests))
                self.assertNotIn("stream", requests[1])
                self.assertEqual(["fast", "fast"], [r["service_tier"] for r in requests])
                self.assertEqual("default", out["service_tier"])

    def test_switched_off_requests_carry_no_tier(self):
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                out, requests = self.call(workflow, [sse(delta("ok"))], payload(""))
                self.assertNotIn("service_tier", requests[0])
                self.assertIsNone(out["service_tier"])

    def test_a_rejected_tier_is_never_resent_without_it(self):
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                error, requests = self.call(
                    workflow, [rejected_tier(), rejected_tier()], payload())
                self.assertIsInstance(error, urllib.error.HTTPError)
                self.assertEqual(400, error.code)
                # The second request is the existing one-time non-streaming
                # attempt; it keeps the tier, so nothing is quietly downgraded.
                self.assertEqual(["priority", "priority"],
                                 [r.get("service_tier") for r in requests])

    def run_batch(self, workflow, tier):
        sent = []

        def call(body):
            sent.append(dict(body))
            raise urllib.error.HTTPError(
                "http://127.0.0.1/chat/completions", 400, "Bad Request", None,
                io.BytesIO(rejected_tier()[2].encode()))

        class Unused(Exception):
            pass

        namespace = selected_namespace(workflow, SIZE_CODE, SIZE_CONSTANTS)
        namespace.update({
            "call": call, "system": "SYSTEM", "MODEL": "fixture", "MAX_OUT": 1000,
            "PAUSEN": [5], "FLUECHTIG": {429, 500, 502, 503, 504},
            "wechsel_passt_noch": lambda what: True,
            "_RelayFehler": Unused, "_ZuGross": Unused,
            "SERVICE_TIER": tier, "KNOWN_TIERS": ("priority",), "OBSERVED_TIERS": [],
            "zeit_fuer_neuen_versuch": lambda pause: True,
        })
        exec(compile(ast.Module([batch_function(workflow)], type_ignores=[]),
                     str(workflow), "exec"), namespace)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as stop:
                namespace["durchsicht"]("INPUT")
        return stop.exception.code, sent, stderr.getvalue()

    def test_http_400_with_a_tier_fails_the_review_once_and_names_the_tier(self):
        for workflow in WORKFLOWS:
            for tier, shown in (("priority", "service_tier=priority"),
                                ("", "service_tier=NONE")):
                with self.subTest(workflow=workflow.name, tier=tier):
                    code, sent, log = self.run_batch(workflow, tier)
                    self.assertEqual(1, code)
                    self.assertEqual(1, len(sent))
                    self.assertEqual(tier or None, sent[0].get("service_tier"))
                    self.assertEqual("xhigh", sent[0]["reasoning_effort"])
                    self.assertIn("Model call failed: HTTP 400", log)
                    self.assertIn(shown, log)
                    self.assertIn("PULLFROG_SERVICE_TIER=off", log)

    def test_only_a_known_answered_tier_is_reported(self):
        for workflow in WORKFLOWS:
            statements = ast.Module(observed_tier_statements(workflow), type_ignores=[])
            known = load_config(workflow, None)["KNOWN_TIERS"]
            for answer, expected in (({"service_tier": "priority"}, "priority"),
                                     ({"service_tier": "default"}, "default"),
                                     ({}, "UNVERIFIED"),
                                     ({"service_tier": None}, "UNVERIFIED"),
                                     ({"service_tier": "PRIORITY"}, "UNVERIFIED"),
                                     ({"service_tier": "<b>fast</b>"}, "UNVERIFIED"),
                                     ({"service_tier": {"tier": "fast"}}, "UNVERIFIED")):
                with self.subTest(workflow=workflow.name, answer=answer):
                    namespace = {"out": answer, "KNOWN_TIERS": known,
                                 "OBSERVED_TIERS": []}
                    exec(compile(statements, str(workflow), "exec"), namespace)
                    self.assertEqual([expected], namespace["OBSERVED_TIERS"])

    def test_review_footer_reports_tiers_and_keeps_its_markers(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        for workflow in WORKFLOWS:
            statement = ast.Module([footer_statement(workflow)], type_ignores=[])
            for tier, observed, expected in (
                    ("priority", ["priority", "priority"],
                     "tier requested priority, observed priority_"),
                    ("priority", ["UNVERIFIED", "default"],
                     "tier requested priority, observed UNVERIFIED, default_"),
                    ("", [], "tier requested NONE, observed UNVERIFIED_")):
                with self.subTest(workflow=workflow.name, tier=tier, observed=observed):
                    namespace = {
                        "lines": [], "MODEL": "fixture", "SERVICE_TIER": tier,
                        "OBSERVED_TIERS": observed, "incomplete": False,
                        "marker": f"<!-- review {sha} -->", "findings": [],
                        "severity_marker": lambda findings: "<!-- severity -->",
                    }
                    exec(compile(statement, str(workflow), "exec"), namespace)
                    lines = namespace["lines"]
                    footer = next(i for i, line in enumerate(lines)
                                  if line.startswith("_fixture · api.airforce"))
                    self.assertTrue(lines[footer].endswith(expected), lines[footer])
                    self.assertEqual(["<!-- severity -->", f"<!-- review {sha} -->"],
                                     lines[footer + 1:footer + 3])


if __name__ == "__main__":
    unittest.main()
