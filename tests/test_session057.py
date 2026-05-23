"""
Session-057 tests: F-126 FIXED (--extra-body warns on callable), F-127 NEW
(warning to stdout pollutes --json), --generate-tests HTTP passthrough fix
(EXTRA_BODY/INPUT_FIELD/OUTPUT_FIELD/AUTH_HEADERS), F-128 NEW (generate-tests
misses behavioral findings), F-123/F-120 still open.
"""

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_dify_server() -> tuple:
    """Start a minimal Dify-style server on a random port. Returns (server, port)."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            if "inputs" not in body or "user" not in body:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing required fields")
                return
            query = body.get("query", "")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"answer": f"Echo: {query}"}).encode())

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)  # port=0 → OS assigns free port
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


_SERVER, _PORT = _start_dify_server()


# ---------------------------------------------------------------------------
# Upstream CI + version checks
# ---------------------------------------------------------------------------

def test_checkagent_version_031():
    """checkagent git main is at 0.3.1."""
    import checkagent
    assert checkagent.__version__ == "0.3.1"


def test_f123_pypi_still_on_030():
    """F-123 still open: PyPI latest is 0.3.0, not 0.3.1.
    Users who run 'pip install checkagent' get 0.3.0 and miss has_refusal +
    literal() fixes and F-120 tracer work."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "index", "versions", "checkagent"],
        capture_output=True, text=True, timeout=30
    )
    combined = result.stdout + result.stderr
    assert "0.3.0" in combined
    assert "LATEST:    0.3.0" in combined or "(0.3.0)" in combined, (
        "F-123: Expected PyPI latest to still be 0.3.0"
    )


# ---------------------------------------------------------------------------
# F-126 FIXED: --extra-body on callable target now warns
# ---------------------------------------------------------------------------

def test_f126_fixed_warning_shown_on_callable():
    """F-126 FIXED: --extra-body on a callable target emits a warning."""
    result = subprocess.run(
        [
            "checkagent", "scan", "agents.echo_agent_simple:run",
            "--extra-body", '{"inputs":{},"user":"test"}',
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, timeout=60
    )
    combined = result.stdout + result.stderr
    assert "extra" in combined.lower() and ("no effect" in combined.lower() or "warning" in combined.lower()), (
        "F-126 FIXED: expected warning about --extra-body on callable target"
    )


def test_f126_fixed_warning_message_content():
    """F-126 FIXED: warning mentions 'callable' and '--url' as context."""
    result = subprocess.run(
        [
            "checkagent", "scan", "agents.echo_agent_simple:run",
            "--extra-body", '{"x":"y"}',
            "--category", "injection",
        ],
        capture_output=True, text=True, timeout=60
    )
    combined = result.stdout + result.stderr
    assert "callable" in combined.lower() or "python" in combined.lower(), (
        "Warning should mention 'callable' or 'Python' targets"
    )
    assert "--url" in combined, "Warning should mention '--url' as the applicable context"


# ---------------------------------------------------------------------------
# F-127 NEW: --extra-body warning goes to stdout, pollutes --json output
# ---------------------------------------------------------------------------

def test_f127_warning_goes_to_stderr_not_stdout():
    """F-127 FIXED (session-058): --extra-body warning on callable goes to stderr,
    so json.loads(result.stdout) works cleanly with --json."""
    result = subprocess.run(
        [
            "checkagent", "scan", "agents.echo_agent_simple:run",
            "--extra-body", '{"x":"y"}',
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, timeout=60
    )
    stdout = result.stdout
    # Warning should NOT be on stdout anymore
    assert not stdout.strip().startswith("Warning:"), (
        f"F-127: Warning unexpectedly on stdout: {stdout[:100]!r}"
    )
    # Naive json.loads on stdout should succeed
    data = json.loads(stdout)
    assert "target" in data
    assert "summary" in data


def test_f127_warning_appears_on_stderr():
    """F-127 FIXED: --extra-body warning goes to stderr (not stdout)."""
    result = subprocess.run(
        [
            "checkagent", "scan", "agents.echo_agent_simple:run",
            "--extra-body", '{"x":"y"}',
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, timeout=60
    )
    # Warning should appear on stderr
    assert "Warning" in result.stderr or "extra-body" in result.stderr, (
        f"Expected warning on stderr: {result.stderr[:200]!r}"
    )


# ---------------------------------------------------------------------------
# --generate-tests HTTP passthrough fix (session-057)
# ---------------------------------------------------------------------------

def test_generate_tests_includes_extra_body():
    """--generate-tests correctly embeds EXTRA_BODY from --extra-body."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        out_path = f.name
    subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--output-field", "answer",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "--generate-tests", out_path,
        ],
        capture_output=True, text=True, timeout=60
    )
    content = open(out_path).read()
    assert "EXTRA_BODY" in content, "Generated test should define EXTRA_BODY constant"
    assert '"inputs"' in content or "'inputs'" in content, "EXTRA_BODY should include 'inputs'"
    assert '"user"' in content or "'user'" in content, "EXTRA_BODY should include 'user'"


def test_generate_tests_includes_input_field():
    """--generate-tests correctly embeds INPUT_FIELD from --input-field."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        out_path = f.name
    subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--output-field", "answer",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "--generate-tests", out_path,
        ],
        capture_output=True, text=True, timeout=60
    )
    content = open(out_path).read()
    assert 'INPUT_FIELD = "query"' in content or "INPUT_FIELD = 'query'" in content, (
        "Generated test should define INPUT_FIELD = 'query'"
    )
    assert 'OUTPUT_FIELD' in content, "Generated test should define OUTPUT_FIELD"


def test_generate_tests_includes_auth_headers():
    """--generate-tests correctly embeds AUTH_HEADERS from -H flags."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        out_path = f.name
    subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "-H", "X-Api-Key: secret123",
            "--generate-tests", out_path,
        ],
        capture_output=True, text=True, timeout=60
    )
    content = open(out_path).read()
    assert "AUTH_HEADERS" in content, "Generated test should define AUTH_HEADERS"
    assert "X-Api-Key" in content, "AUTH_HEADERS should include custom header"
    assert "secret123" in content, "AUTH_HEADERS should include header value"


def test_generate_tests_payload_uses_extra_body():
    """Generated test payload merges EXTRA_BODY with INPUT_FIELD."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        out_path = f.name
    subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "--generate-tests", out_path,
        ],
        capture_output=True, text=True, timeout=60
    )
    content = open(out_path).read()
    # The agent_fn should merge EXTRA_BODY + probe input
    assert "{**EXTRA_BODY" in content, (
        "Generated test payload should merge EXTRA_BODY: {**EXTRA_BODY, INPUT_FIELD: ...}"
    )


# ---------------------------------------------------------------------------
# F-128 NEW: --generate-tests uses evaluate_output (static) not baseline comparison
# ---------------------------------------------------------------------------

def test_f128_generated_tests_now_match_scan_findings():
    """F-128 FIXED (session-058): generated tests use evaluate_output_with_baseline()
    and catch behavioral findings (length_anomaly, new_code_blocks, etc.).
    Generated test failures should be >= scan findings (not fewer)."""
    # Run the scan and count detected findings
    scan_result = subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "--json",
        ],
        capture_output=True, text=True, timeout=60
    )
    scan_data = json.loads(scan_result.stdout)
    scan_failed = scan_data["summary"]["failed"]  # probes with findings in scan

    # Generate tests and run them against the live server
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        out_path = f.name
    subprocess.run(
        [
            "checkagent", "scan",
            f"--url=http://127.0.0.1:{_PORT}/",
            "--input-field", "query",
            "--extra-body", '{"inputs":{},"user":"testuser"}',
            "--category", "injection",
            "--generate-tests", out_path,
        ],
        capture_output=True, text=True, timeout=60
    )
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", out_path, "-q", "--tb=no"],
        capture_output=True, text=True, timeout=120
    )
    # Count test failures (tests that correctly flagged the agent as unsafe)
    test_output = test_result.stdout + test_result.stderr
    import re
    m = re.search(r"(\d+) failed", test_output)
    test_failed = int(m.group(1)) if m else 0

    # F-128 FIXED: generated tests should now catch AT LEAST as many findings as the scan
    assert test_failed >= scan_failed, (
        f"F-128 regression: Generated tests only caught {test_failed} findings, "
        f"but scan found {scan_failed}. Baseline comparison may be broken."
    )


# ---------------------------------------------------------------------------
# F-120 still open: auto-instrumentation tracer returns no events
# ---------------------------------------------------------------------------

def test_f120_still_open_tracer_events_empty():
    """F-120 still open: begin_probe_trace/end_probe_trace are stubs.
    end_probe_trace() always returns [] regardless of activity."""
    from checkagent.core.tracer import (
        install_patches, uninstall_patches,
        begin_probe_trace, end_probe_trace, is_installed
    )
    install_patches()
    assert is_installed()
    token = begin_probe_trace()
    events = end_probe_trace()
    uninstall_patches()

    assert events == [], (
        f"F-120 still open: expected empty events from tracer stub, got {events}"
    )
