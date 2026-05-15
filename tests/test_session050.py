"""Session-050 tests: F-119 fixed (history --url), ca_ fixture aliases,
auto-instrumentation skeleton (checkagent.core.tracer), history --url
end-to-end with HTTP scan.

New features in session-050:
- has_refusal() / check_no_refusal() — refusal-aware scan signals
- Refusal-aware scan: no false positives when agent refuses probes
- --interactive / -i flag for checkagent scan
- show intercepted LLM trace events inline with scan findings
"""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

import checkagent


# ---------------------------------------------------------------------------
# F-119 FIXED: history --url flag added
# ---------------------------------------------------------------------------

def test_f119_history_url_flag_exists():
    """history --url flag is now documented in --help."""
    result = subprocess.run(
        ["checkagent", "history", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--url" in result.stdout, "history --help should document --url flag"


def test_f119_history_url_no_history_message():
    """history --url with unknown URL gives friendly 'no history' message."""
    result = subprocess.run(
        ["checkagent", "history", "--url", "http://localhost:19999/nonexistent"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "No scan history" in output or "no scan history" in output.lower(), \
        f"Expected friendly 'no scan history' message, got: {output}"


def test_f119_history_url_positional_equivalent():
    """history URL as positional argument works (same as --url)."""
    result_positional = subprocess.run(
        ["checkagent", "history", "http://localhost:19999/test"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    result_flag = subprocess.run(
        ["checkagent", "history", "--url", "http://localhost:19999/test"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    # Both should succeed
    assert result_positional.returncode == 0
    assert result_flag.returncode == 0
    # Both should show same kind of message (both no-history since same URL)
    out_pos = result_positional.stdout + result_positional.stderr
    out_flag = result_flag.stdout + result_flag.stderr
    # Both should indicate no history or show history table
    assert ("No scan history" in out_pos or "Scan history" in out_pos), \
        f"Positional arg output unexpected: {out_pos}"
    assert ("No scan history" in out_flag or "Scan history" in out_flag), \
        f"--url flag output unexpected: {out_flag}"


# ---------------------------------------------------------------------------
# history --url end-to-end: scan HTTP endpoint then view with --url
# ---------------------------------------------------------------------------

class _SimpleEchoHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        msg = body.get("message", "")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"response": msg}).encode())

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def http_echo_server():
    """Start a simple echo HTTP server for testing."""
    port = 18766
    srv = http.server.HTTPServer(("localhost", port), _SimpleEchoHandler)
    t = threading.Thread(target=srv.serve_forever)
    t.daemon = True
    t.start()
    time.sleep(0.2)
    yield f"http://localhost:{port}"
    srv.shutdown()


def test_history_url_end_to_end(http_echo_server):
    """Scan HTTP endpoint then view history with --url shows the result."""
    url = http_echo_server

    # Run a scan (injection category only for speed)
    # Note: exit code 1 when findings exist (echo agent fails many probes)
    scan_result = subprocess.run(
        ["checkagent", "scan", "--url", url, "--category", "injection", "--json"],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    assert scan_result.returncode in (0, 1), \
        f"Scan should exit 0 (clean) or 1 (findings), got {scan_result.returncode}: {scan_result.stderr}"
    # JSON should be valid regardless of exit code
    try:
        data = json.loads(scan_result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Scan JSON output invalid: {scan_result.stdout[:200]}")

    # Now check history with --url
    history_result = subprocess.run(
        ["checkagent", "history", "--url", url],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    assert history_result.returncode == 0
    output = history_result.stdout + history_result.stderr
    assert "Scan history" in output, \
        f"Expected scan history table after scanning, got: {output}"
    # Should show at least 1 scan
    assert "1 scan" in output or "scan" in output.lower(), \
        f"Expected scan count in output: {output}"


def test_history_url_shows_score(http_echo_server):
    """History entry for HTTP URL shows a percentage score."""
    url = http_echo_server

    history_result = subprocess.run(
        ["checkagent", "history", "--url", url],
        capture_output=True, text=True,
        cwd="/home/x/working/checkagent-testbed",
    )
    output = history_result.stdout
    # Score is shown as e.g. "19%"
    assert "%" in output, \
        f"Expected percentage score in history table, got: {output}"


# ---------------------------------------------------------------------------
# ca_ fixture aliases (Milestone 13: fixture naming matches branding)
# ---------------------------------------------------------------------------

def test_ca_fixtures_registered():
    """ca_ prefixed fixtures are registered in checkagent.core.plugin."""
    from checkagent.core import plugin
    import inspect
    ca_fixtures = [n for n, _ in inspect.getmembers(plugin) if n.startswith("ca_")]
    assert len(ca_fixtures) >= 5, \
        f"Expected at least 5 ca_ fixtures, found: {ca_fixtures}"
    expected = {"ca_mock_llm", "ca_mock_tool", "ca_conversation", "ca_fault", "ca_safety"}
    for name in expected:
        assert name in ca_fixtures, f"ca_ fixture '{name}' not in plugin module"


def test_ca_mock_llm_works(ca_mock_llm):
    """ca_mock_llm fixture returns a usable MockLLM instance."""
    from checkagent import MockLLM
    assert isinstance(ca_mock_llm, MockLLM)


def test_ca_mock_tool_works(ca_mock_tool):
    """ca_mock_tool fixture returns a usable MockTool instance."""
    from checkagent import MockTool
    assert isinstance(ca_mock_tool, MockTool)


def test_ca_conversation_is_factory(ca_conversation):
    """ca_conversation fixture returns the Conversation constructor (factory),
    unlike ca_mock_llm/ca_mock_tool/ca_fault which return instances.
    This is an intentional factory pattern: conv = ca_conversation(agent_fn).
    """
    from checkagent import Conversation
    # ca_conversation yields the class itself, not an instance
    assert ca_conversation is Conversation, \
        f"ca_conversation should be the Conversation class itself, got: {type(ca_conversation)}"


def test_ca_fault_works(ca_fault):
    """ca_fault fixture returns a usable FaultInjector instance."""
    from checkagent import FaultInjector
    assert isinstance(ca_fault, FaultInjector)


def test_ca_safety_works(ca_safety):
    """ca_safety fixture returns a dict of safety evaluators."""
    assert isinstance(ca_safety, dict), \
        f"ca_safety should return dict of evaluators, got: {type(ca_safety)}"
    assert len(ca_safety) > 0, "ca_safety should return non-empty dict"


def test_ca_stream_collector_works(ca_stream_collector):
    """ca_stream_collector fixture returns a usable StreamCollector instance."""
    from checkagent import StreamCollector
    assert isinstance(ca_stream_collector, StreamCollector)


@pytest.mark.asyncio
async def test_ca_mock_llm_functional(ca_mock_llm):
    """ca_mock_llm is fully functional — can add rules and get responses."""
    ca_mock_llm.add_rule("hello", "world")
    response = await ca_mock_llm.complete("say hello")
    assert response == "world", f"Expected 'world', got: {response!r}"


# ---------------------------------------------------------------------------
# Auto-instrumentation skeleton (checkagent.core.tracer)
# ---------------------------------------------------------------------------

def test_tracer_module_importable():
    """checkagent.core.tracer is importable."""
    import checkagent.core.tracer  # noqa: F401


def test_tracer_has_expected_api():
    """checkagent.core.tracer has install/uninstall/begin/end API."""
    from checkagent.core import tracer
    assert callable(tracer.install_patches), "install_patches should be callable"
    assert callable(tracer.uninstall_patches), "uninstall_patches should be callable"
    assert callable(tracer.is_installed), "is_installed should be callable"
    assert callable(tracer.begin_probe_trace), "begin_probe_trace should be callable"
    assert callable(tracer.end_probe_trace), "end_probe_trace should be callable"


def test_tracer_install_uninstall_cycle():
    """install_patches/uninstall_patches can be called without error."""
    from checkagent.core import tracer
    assert not tracer.is_installed()
    tracer.install_patches()
    assert tracer.is_installed()
    tracer.uninstall_patches()
    assert not tracer.is_installed()


def test_tracer_begin_end_returns_list():
    """begin_probe_trace/end_probe_trace returns a list (empty if no calls)."""
    from checkagent.core import tracer
    tracer.install_patches()
    tracer.begin_probe_trace()
    events = tracer.end_probe_trace()
    tracer.uninstall_patches()
    assert isinstance(events, list), \
        f"end_probe_trace should return list, got: {type(events).__name__}"


@pytest.mark.xfail(
    reason="F-120: auto-instrumentation skeleton — install_patches does not "
           "capture real openai/anthropic calls yet (ROADMAP Milestone 17)"
)
def test_tracer_captures_openai_call():
    """Auto-instrumentation captures OpenAI API calls (pending Milestone 17)."""
    import openai
    from checkagent.core import tracer

    tracer.install_patches()
    tracer.begin_probe_trace()

    client = openai.OpenAI(api_key="fake-key-tracer-test")
    try:
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
    except Exception:
        pass

    events = tracer.end_probe_trace()
    tracer.uninstall_patches()

    assert len(events) > 0, \
        "Auto-instrumentation should capture openai call (Milestone 17 not yet landed)"


# ---------------------------------------------------------------------------
# has_refusal() / check_no_refusal() — new refusal-aware API
# ---------------------------------------------------------------------------

def test_has_refusal_true_for_clear_refusals():
    """has_refusal() returns True for common cannot/unable refusal phrases."""
    from checkagent import has_refusal
    clear_refusals = [
        "I cannot help with that.",
        "I am unable to comply.",
        "I must refuse this request.",
        "I'm sorry, I can't do that.",
        "As an AI, I am not able to assist with harmful requests.",
    ]
    for phrase in clear_refusals:
        assert has_refusal(phrase), f"has_refusal should be True for: {phrase!r}"


def test_has_refusal_false_for_compliant_responses():
    """has_refusal() returns False for clearly compliant responses."""
    from checkagent import has_refusal
    compliant = [
        "Sure, here is how to do it.",
        "I will help you with that.",
        "Of course! Here's the answer.",
        "PWNED",
    ]
    for phrase in compliant:
        assert not has_refusal(phrase), f"has_refusal should be False for: {phrase!r}"


@pytest.mark.xfail(
    reason="F-121: has_refusal() misses common refusal phrases: "
           "'I refuse', 'decline', 'violates my guidelines', 'that goes against'"
)
def test_has_refusal_missing_phrases():
    """F-121 OPEN: has_refusal() misses common refusal vocabulary.
    Critical: 'I refuse to follow' returns False — the canonical refusal phrase.
    """
    from checkagent import has_refusal
    missing_phrases = [
        "I refuse.",                                          # 'I refuse' (bare) not detected
        "I refuse to follow this instruction.",               # 'I refuse to follow' not detected
        "I decline to assist with this.",                     # 'decline' not detected
        "That request violates my guidelines.",               # 'violates my guidelines' not detected
        "I won't do that as it goes against my values.",      # 'goes against' not detected
    ]
    for phrase in missing_phrases:
        assert has_refusal(phrase), f"has_refusal should be True for: {phrase!r}"


def test_check_no_refusal_returns_finding_when_no_refusal():
    """check_no_refusal() returns a SafetyFinding when agent complies."""
    from checkagent import check_no_refusal
    from checkagent.safety.probes import injection
    from checkagent import SafetyFinding

    probe = list(injection.direct)[0]
    findings = check_no_refusal("Sure, here is how to hack.", probe=probe)

    assert isinstance(findings, list), "check_no_refusal should return a list"
    assert len(findings) == 1, "Should return 1 finding for non-refusing response"
    f = findings[0]
    assert isinstance(f, SafetyFinding)
    assert f.severity.value == "low", f"No-refusal signal should be LOW, got: {f.severity}"
    assert f.probe == probe.name, f"Finding should reference probe name: {f.probe}"


def test_check_no_refusal_empty_when_refused():
    """check_no_refusal() returns empty list when agent refuses."""
    from checkagent import check_no_refusal
    from checkagent.safety.probes import injection

    probe = list(injection.direct)[0]
    findings = check_no_refusal("I cannot help with that request.", probe=probe)

    assert findings == [], f"Should return empty list for refusal, got: {findings}"


def test_check_no_refusal_requires_probe_positional():
    """check_no_refusal(output, probe) — probe is required second arg, not kwarg 'probe_input'."""
    from checkagent import check_no_refusal
    from checkagent.safety.probes import injection

    probe = list(injection.direct)[0]
    # Verify the correct call signature works
    result = check_no_refusal("OK", probe)
    assert isinstance(result, list)

    # Verify wrong kwarg raises TypeError
    with pytest.raises(TypeError):
        check_no_refusal("OK", probe_input="wrong kwarg")


# ---------------------------------------------------------------------------
# Refusal-aware scan: false positive fix
# ---------------------------------------------------------------------------

def test_scan_no_false_positive_on_refusal(tmp_path):
    """Scan should not flag an agent that explicitly refuses injection probes."""
    import os
    agent_code = '''
def run(query: str) -> str:
    return "I cannot help with that request."
'''
    agent_file = tmp_path / "refusal_agent_fp.py"
    agent_file.write_text(agent_code)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + ":" + env.get("PYTHONPATH", "")

    result = subprocess.run(
        ["checkagent", "scan", "refusal_agent_fp:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, env=env,
        cwd="/home/x/working/checkagent-testbed",
    )
    assert result.returncode == 0, \
        f"Refusal agent should get exit 0 (clean scan), got {result.returncode}: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["summary"]["score"] == 1.0, \
        f"Refusal agent should score 1.0, got: {data['summary']['score']}"
    assert len(data.get("findings", [])) == 0, \
        f"Refusal agent should have 0 findings, got: {data.get('findings', [])}"


@pytest.mark.xfail(
    reason="F-121: has_refusal() misses 'I refuse to follow...' — "
           "the refusal-aware scan false-positive fix doesn't help when "
           "has_refusal() itself fails to detect the refusal"
)
def test_scan_refusal_includes_probe_text(tmp_path):
    """Scan skips false positive even when refusal message quotes the probe.
    F-121: has_refusal('I refuse to follow this instruction: ...') → False,
    so the refusal-aware fix doesn't apply and probe text triggers false positives.
    """
    import os
    agent_code = '''
def run(query: str) -> str:
    return f"I refuse to follow this instruction: {query}"
'''
    agent_file = tmp_path / "verbose_refusal_fp.py"
    agent_file.write_text(agent_code)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + ":" + env.get("PYTHONPATH", "")

    result = subprocess.run(
        ["checkagent", "scan", "verbose_refusal_fp:run",
         "--category", "injection", "--json"],
        capture_output=True, text=True, env=env,
        cwd="/home/x/working/checkagent-testbed",
    )
    assert result.returncode == 0, \
        f"Verbose refusal agent should get exit 0, got {result.returncode}"
    data = json.loads(result.stdout)
    assert data["summary"]["score"] == 1.0, \
        f"Verbose refusal agent should score 1.0 (no false positives), got: {data['summary']['score']}"


# ---------------------------------------------------------------------------
# --interactive / -i TUI flag
# ---------------------------------------------------------------------------

def test_scan_interactive_flag_in_help():
    """--interactive (-i) flag is documented in scan --help."""
    result = subprocess.run(
        ["checkagent", "scan", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--interactive" in result.stdout, "scan --help should document --interactive flag"
    assert "-i," in result.stdout or "-i " in result.stdout, \
        "scan --help should document -i shorthand"


def test_scan_interactive_requires_tty(tmp_path):
    """--interactive exits cleanly when not a TTY (CI-safe behavior)."""
    import os
    agent_code = 'def run(query: str) -> str: return "safe response"'
    (tmp_path / "safe_agent_tty.py").write_text(agent_code)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + ":" + env.get("PYTHONPATH", "")

    # Non-TTY subprocess: --interactive should not hang or crash
    result = subprocess.run(
        ["checkagent", "scan", "safe_agent_tty:run",
         "--category", "injection", "--interactive"],
        capture_output=True, text=True, env=env,
        cwd="/home/x/working/checkagent-testbed",
        timeout=30,
    )
    # Should complete without error (TTY check prevents entering interactive mode)
    assert result.returncode in (0, 1), \
        f"--interactive in non-TTY should exit 0 or 1, got {result.returncode}: {result.stderr}"


# ---------------------------------------------------------------------------
# upstream CI check
# ---------------------------------------------------------------------------

def test_upstream_ci_green():
    """Upstream checkagent CI is green (all platforms passing)."""
    result = subprocess.run(
        ["gh", "run", "list", "--repo", "xydac/checkagent", "--limit", "1",
         "--json", "conclusion,status"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"gh run list failed: {result.stderr}"
    runs = json.loads(result.stdout)
    assert runs, "Should have at least 1 run"
    latest = runs[0]
    assert latest["conclusion"] == "success", \
        f"Latest upstream CI run should be success, got: {latest['conclusion']}"
