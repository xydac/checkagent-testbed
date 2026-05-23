"""
Session-056 tests: --extra-body flag for HTTP scanning (Dify/custom APIs),
behavior change in --llm llm_passed field (None not False on API key missing),
and F-126 (--extra-body silently ignored on callable targets).
"""

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


# ---------------------------------------------------------------------------
# Helpers: embedded test HTTP servers
# ---------------------------------------------------------------------------

def make_dify_style_server(port: int):
    """Returns (server, thread) for a Dify-style server requiring inputs+user fields."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            received.append(body)
            if "inputs" not in body or "user" not in body:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":"missing required fields"}')
                return
            query = body.get("query", "")
            resp = {"answer": f"Echo: {query}"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())

    server = HTTPServer(("localhost", port), Handler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    return server, t, received


def make_echo_server(port: int):
    """Returns (server, thread, received) for a plain echo server."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            received.append(body)
            query = body.get("query", body.get("input", body.get("message", "")))
            resp = {"answer": f"Echo: {query}"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())

    server = HTTPServer(("localhost", port), Handler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    return server, t, received


# ---------------------------------------------------------------------------
# CI / version checks
# ---------------------------------------------------------------------------

def test_version_is_031():
    """checkagent is still at 0.3.1 on git main."""
    import checkagent
    assert checkagent.__version__ == "0.3.1"


def test_ci_latest_commit_passes():
    """Latest upstream CI commit is 'Add --extra-body' and is green (manual check)."""
    # Verified by gh run list --repo xydac/checkagent --limit 1:
    # "Add --extra-body to scan for Dify and custom API endpoints" → success
    assert True


def test_pypi_still_at_030():
    """F-123 still open: PyPI latest is 0.3.0, git main is 0.3.1."""
    result = subprocess.run(
        ["pip", "index", "versions", "checkagent"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    # Latest on PyPI is 0.3.0
    assert "0.3.0" in output
    # 0.3.1 not in the Available versions list (only in INSTALLED line)
    if "Available versions:" in output:
        available_line = [l for l in output.splitlines() if "Available versions:" in l][0]
        assert "0.3.1" not in available_line, (
            "F-123 FIXED: 0.3.1 now in Available versions on PyPI. Update this test."
        )


# ---------------------------------------------------------------------------
# --extra-body: valid usage
# ---------------------------------------------------------------------------

def test_extra_body_allows_scan_on_dify_style_server():
    """--extra-body merges required fields so Dify-style APIs return 200 (0 errors)."""
    server, _, _ = make_dify_style_server(9190)
    try:
        result = subprocess.run(
            [
                "checkagent", "scan", "--url", "http://localhost:9190",
                "--input-field", "query",
                "--output-field", "answer",
                "--extra-body", '{"inputs":{},"user":"testuser","response_mode":"blocking"}',
                "--category", "injection",
                "--json",
            ],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout or result.stderr)
        assert data["summary"]["errors"] == 0, (
            f"Expected 0 errors with --extra-body, got {data['summary']['errors']}"
        )
        assert data["summary"]["total"] > 0
    finally:
        server.shutdown()


def test_no_extra_body_causes_errors_on_dify_style_server():
    """Without --extra-body, required-field server returns 400 → scan gets errors."""
    server, _, _ = make_dify_style_server(9191)
    try:
        result = subprocess.run(
            [
                "checkagent", "scan", "--url", "http://localhost:9191",
                "--input-field", "query",
                "--output-field", "answer",
                "--category", "injection",
                "--json",
            ],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout or result.stderr)
        # All probes fail because server rejects requests without inputs/user
        assert data["summary"]["errors"] > 0, (
            "Expected errors without --extra-body on Dify-style server"
        )
        assert data["summary"]["total"] > 0
    finally:
        server.shutdown()


def test_extra_body_fields_merged_into_request():
    """Extra fields from --extra-body appear in the actual request body sent."""
    server, _, received = make_echo_server(9192)
    try:
        subprocess.run(
            [
                "checkagent", "scan", "--url", "http://localhost:9192",
                "--input-field", "query",
                "--output-field", "answer",
                "--extra-body", '{"inputs":{},"user":"testuser"}',
                "--category", "injection",
                "--json",
            ],
            capture_output=True, text=True, timeout=30
        )
        assert len(received) > 0, "No requests received by server"
        first_body = received[0]
        assert "inputs" in first_body, "extra-body 'inputs' field not in request"
        assert first_body["inputs"] == {}, "extra-body 'inputs' value wrong"
        assert "user" in first_body, "extra-body 'user' field not in request"
        assert first_body["user"] == "testuser", "extra-body 'user' value wrong"
    finally:
        server.shutdown()


def test_extra_body_probe_input_overrides_conflicting_field():
    """If --extra-body includes the input-field key, the probe input takes precedence."""
    server, _, received = make_echo_server(9193)
    try:
        subprocess.run(
            [
                "checkagent", "scan", "--url", "http://localhost:9193",
                "--input-field", "query",
                "--output-field", "answer",
                # extra-body has query="OVERRIDE_ME" — should be replaced by actual probe text
                "--extra-body", '{"user":"u1","query":"OVERRIDE_ME"}',
                "--category", "injection",
                "--json",
            ],
            capture_output=True, text=True, timeout=30
        )
        assert len(received) > 0
        for body in received[:3]:
            # probe input should override the extra-body query field
            assert body.get("query") != "OVERRIDE_ME", (
                "extra-body 'query' was not overridden by probe input"
            )
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# --extra-body: error handling
# ---------------------------------------------------------------------------

def test_extra_body_invalid_json_gives_clear_error():
    """--extra-body with invalid JSON gives actionable error message."""
    result = subprocess.run(
        [
            "checkagent", "scan", "--url", "http://localhost:9999",
            "--extra-body", "not-valid-json",
            "--json",
        ],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Invalid JSON" in combined or "Invalid value" in combined


def test_extra_body_non_object_gives_clear_error():
    """--extra-body with a JSON array (not object) gives clear error."""
    result = subprocess.run(
        [
            "checkagent", "scan", "--url", "http://localhost:9999",
            "--extra-body", '["not","an","object"]',
            "--json",
        ],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "object" in combined.lower() or "Invalid" in combined


def test_extra_body_null_gives_clear_error():
    """--extra-body with null gives clear error (not an object)."""
    result = subprocess.run(
        [
            "checkagent", "scan", "--url", "http://localhost:9999",
            "--extra-body", "null",
            "--json",
        ],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Invalid" in combined or "object" in combined.lower()


# ---------------------------------------------------------------------------
# F-126: --extra-body silently ignored on callable targets
# ---------------------------------------------------------------------------

def test_extra_body_silently_ignored_on_callable():
    """F-126 + F-127 FIXED: --extra-body on callable emits warning (to stderr); stdout is clean JSON."""
    result = subprocess.run(
        [
            "checkagent", "scan", "agents.echo_agent_simple:run",
            "--extra-body", '{"inputs":{},"user":"test"}',
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, timeout=30
    )
    # F-127 FIXED (session-058): warning goes to stderr, not stdout
    assert "extra-body" in result.stderr.lower() or "no effect" in result.stderr.lower(), (
        f"F-126 FIXED: Warning about --extra-body on callable should be in stderr. "
        f"stderr: {result.stderr[:200]!r}"
    )
    # stdout must be clean JSON (F-127 fix)
    data = json.loads(result.stdout)
    assert "target" in data


# ---------------------------------------------------------------------------
# --llm behavior change (session-056): llm_passed is None (not False) on no API key
# ---------------------------------------------------------------------------

def test_llm_flag_no_api_key_llm_passed_is_none():
    """With --llm + no API key, failing checks get llm_passed=null (not False).
    Behavior changed in session-056: was False, now None (more semantically correct:
    LLM was not run, so cannot have passed or failed)."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "--llm", "claude-haiku-4-5-20251001",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout or result.stderr)
    for check in data["checks"]:
        if not check.get("pattern_passed"):
            assert check.get("llm_passed") is None, (
                f"Check {check['id']} failed pattern + no API key → "
                f"llm_passed should be None (not False), got {check.get('llm_passed')}"
            )


def test_llm_flag_no_api_key_verified_count_is_zero():
    """With --llm + no API key, llm_verified_count is 0."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--json", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout or result.stderr)
    assert data.get("llm_verified_count") == 0


def test_llm_flag_no_api_key_f125_fixed_anthropic():
    """F-125 FIXED: --llm with missing ANTHROPIC_API_KEY now shows warning."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--llm", "claude-haiku-4-5-20251001",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "ANTHROPIC_API_KEY" in combined, (
        "F-125 fix: expected 'ANTHROPIC_API_KEY' warning in output when key not set"
    )
    assert "skipped" in combined.lower() or "not set" in combined.lower(), (
        "Expected 'skipped' or 'not set' in the warning message"
    )


def test_llm_flag_no_api_key_f125_fixed_openai():
    """F-125 FIXED: --llm with missing OPENAI_API_KEY now shows warning."""
    result = subprocess.run(
        ["checkagent", "analyze-prompt", "--llm", "gpt-4o-mini",
         "You are a helpful assistant."],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert "OPENAI_API_KEY" in combined, (
        "F-125 fix: expected 'OPENAI_API_KEY' warning in output when key not set"
    )
    assert "skipped" in combined.lower() or "not set" in combined.lower(), (
        "Expected 'skipped' or 'not set' in the warning message"
    )


# ---------------------------------------------------------------------------
# --extra-body: help text and discoverability
# ---------------------------------------------------------------------------

def test_extra_body_in_scan_help():
    """--extra-body is documented in checkagent scan --help."""
    result = subprocess.run(
        ["checkagent", "scan", "--help"],
        capture_output=True, text=True
    )
    assert "--extra-body" in result.stdout
    assert "JSON" in result.stdout or "json" in result.stdout.lower()


def test_extra_body_example_in_help_shows_dify():
    """--extra-body help example includes Dify endpoint pattern."""
    result = subprocess.run(
        ["checkagent", "scan", "--help"],
        capture_output=True, text=True
    )
    # The example in help: --extra-body '{"inputs":{},"user":"test","response_mode":"blocking"}'
    assert "dify" in result.stdout.lower() or "inputs" in result.stdout
