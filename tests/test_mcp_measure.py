from pathlib import Path

from scripts import measure_mcp
from scripts.measure_mcp import compare_baseline


def _current():
    return {
        "server_startup_seconds": 7.0,
        "first_query_seconds": 7.0,
        "hot_query_seconds": 0.00018,
        "passed": True,
    }


def test_mcp_baseline_allows_up_to_twenty_percent_regression():
    payload = compare_baseline(
        _current(),
        {
            "server_startup_seconds": 6.0,
            "first_query_seconds": 6.0,
            "hot_query_seconds": 0.00016,
        },
    )
    assert payload["passed"] is True
    assert payload["baseline"]["passed"] is True


def test_mcp_baseline_fails_when_a_metric_regresses_too_far():
    payload = compare_baseline(
        _current(),
        {
            "server_startup_seconds": 5.0,
            "first_query_seconds": 6.0,
            "hot_query_seconds": 0.00016,
        },
    )
    assert payload["passed"] is False
    assert any(item["metric"] == "server_startup_seconds" for item in payload["baseline"]["failures"])


def test_mcp_baseline_rejects_missing_or_nonpositive_metrics():
    payload = compare_baseline(_current(), {})
    assert payload["passed"] is False
    assert len(payload["baseline"]["failures"]) == 3


def test_submillisecond_tolerance_is_stable_at_float_boundary():
    payload = compare_baseline(
        {
            "server_startup_seconds": 6.0,
            "first_query_seconds": 6.0,
            "hot_query_seconds": 0.000385700026,
            "passed": True,
        },
        {
            "server_startup_seconds": 6.0,
            "first_query_seconds": 6.0,
            "hot_query_seconds": 0.0001857,
        },
    )
    assert payload["passed"] is True


def test_mcp_cli_returns_nonzero_for_failed_report(monkeypatch):
    monkeypatch.setattr(
        measure_mcp,
        "measure",
        lambda *args, **kwargs: {
            "server_startup_seconds": 1.0,
            "first_query_seconds": 1.0,
            "hot_query_seconds": 0.1,
            "passed": False,
        },
    )

    assert measure_mcp.main(["--db", "db", "--model", "fake"]) == 1


def test_mcp_startup_metric_stops_at_initialize_readiness(monkeypatch):
    class FakeProcess:
        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

    process = FakeProcess()
    captured = {}

    def fake_popen(*args, **kwargs):
        captured.update(kwargs)
        return process

    monkeypatch.setenv("PYTHONPATH", "selected-installation")
    monkeypatch.setattr(measure_mcp.subprocess, "Popen", fake_popen)
    ticks = iter((10.0, 10.2))
    monkeypatch.setattr(measure_mcp.time, "perf_counter", lambda: next(ticks))
    roundtrips = iter((
        ({"result": {}}, 1.5),
        ({"result": {}}, 2.0),
        ({"result": {}}, 0.1),
    ))
    monkeypatch.setattr(measure_mcp, "_roundtrip", lambda *args, **kwargs: next(roundtrips))

    payload = measure_mcp.measure(Path("db"), "fake", "query")
    assert round(payload["process_spawn_seconds"], 3) == 0.2
    assert payload["server_startup_seconds"] == 1.5
    assert payload["first_query_seconds"] == 2.0
    assert payload["hot_query_seconds"] == 0.1
    assert captured["env"]["PYTHONPATH"] == "selected-installation"
