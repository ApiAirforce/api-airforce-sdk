"""Synthetic SSE completion boundaries for the SDK pull request reviewer."""

import ast
import contextlib
import io
import json
import re
import sys
import textwrap
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch


WORKFLOW = Path(__file__).resolve().parents[1] / "workflows" / "review.yml"


class StreamUnusable(Exception):
    pass


class EventStream:
    class Headers:
        @staticmethod
        def get_content_type():
            return "text/event-stream"

    headers = Headers()

    def __init__(self, frames):
        self.lines = []
        for frame in frames:
            data = frame if isinstance(frame, str) else json.dumps(frame)
            self.lines.extend((f"data: {data}\n".encode(), b"\n"))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __iter__(self):
        return iter(self.lines)


def stream_reader():
    source = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"python3 - <<'PYEOF'\r?\n(.*?)\r?\n\s+PYEOF", source, re.S)
    if not match:
        raise AssertionError("embedded reviewer script missing")
    script = textwrap.dedent(match.group(1))
    functions = [node for node in ast.parse(script).body
                 if isinstance(node, ast.FunctionDef) and node.name == "_stroemen"]
    if len(functions) != 1:
        raise AssertionError("expected one stream transport")
    namespace = {
        "BASE": "https://example.invalid", "KEY": "fixture",
        "_RelayFehler": RuntimeError, "_StromUnbrauchbar": StreamUnusable,
        "_relay_fehler": lambda _: None,
        "json": json, "sys": sys, "urllib": urllib,
    }
    exec(compile(ast.Module(functions, type_ignores=[]), str(WORKFLOW), "exec"),
         namespace)
    return namespace["_stroemen"]


class ReviewStreamCompletionTests(unittest.TestCase):
    def invoke(self, frames):
        with patch.object(urllib.request, "urlopen",
                          return_value=EventStream(frames)) as transport:
            result = stream_reader()({"messages": []})
            transport.assert_called_once()
            return result

    def test_stop_without_done_returns_complete_response_shape(self):
        content = {"choices": [{"delta": {"content": "review"}}]}
        stop = {"choices": [{"finish_reason": "stop"}],
                "usage": {"total_tokens": 7}}
        result = self.invoke((content, stop))
        self.assertEqual("review", result["choices"][0]["message"]["content"])
        self.assertEqual(7, result["usage"]["total_tokens"])
        with self.assertRaisesRegex(StreamUnusable, "without content"):
            self.invoke((stop,))

    def test_eof_and_non_stop_reasons_cannot_complete_a_review(self):
        content = {"choices": [{"delta": {"content": "partial"}}]}
        stop = {"choices": [{"finish_reason": "stop"}]}
        with self.assertRaisesRegex(StreamUnusable, "without completion"):
            self.invoke((content,))
        result = self.invoke((content, "[DONE]"))
        self.assertEqual("partial", result["choices"][0]["message"]["content"])
        for reason in ("length", "content_filter", "other"):
            terminal = {"choices": [{"finish_reason": reason}]}
            for frames in ((content, terminal),
                           (content, terminal, stop),
                           (content, terminal, "[DONE]"),
                           (content, stop, terminal)):
                with self.subTest(reason=reason, frames=frames):
                    with self.assertRaisesRegex(StreamUnusable,
                                                "non-stop terminal reason"):
                        self.invoke(frames)

    def test_malformed_events_fail_first_without_logging_event_data(self):
        content = {"choices": [{"message": {"content": "review"}}]}
        stop = {"choices": [{"finish_reason": "stop"}]}
        private_event = "{private-review-event"
        for frames in ((private_event,),
                       (private_event, "[DONE]"),
                       (content, private_event, stop),
                       (content, [], "[DONE]")):
            with self.subTest(frames=frames):
                log = io.StringIO()
                with contextlib.redirect_stderr(log), \
                     self.assertRaisesRegex(StreamUnusable,
                                            "1 unreadable SSE events") as caught:
                    self.invoke(frames)
                diagnostic = str(caught.exception) + log.getvalue()
                self.assertNotIn(private_event, diagnostic)
                self.assertNotIn("without content", diagnostic)
                self.assertNotIn("without completion", diagnostic)


if __name__ == "__main__":
    unittest.main()
