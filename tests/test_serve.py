"""MCP stdio server contract tests (initialize / tools/list / tools/call)."""

import io
import json

from ue_knowledge.build import build_index
from ue_knowledge.server import serve_loop

from fake_embedder import FakeEmbedder


def _corpus(tmp_path):
    directory = tmp_path / "corpus"
    topic = directory / "ue-character-movement"
    topic.mkdir(parents=True)
    (topic / "doc.md").write_text(
        "# Movement\n\n" + ("movement speed braking " * 30), encoding="utf-8"
    )
    return directory


def _run_server(input_lines, db, embedder):
    stdin = io.StringIO("\n".join(input_lines) + "\n")
    stdout = io.StringIO()
    serve_loop(
        stdin, stdout, chroma_dir=str(db), model_name="fake",
        embedder=embedder, top_k=3,
    )
    return [json.loads(line) for line in stdout.getvalue().strip().splitlines()]


def test_initialize_and_tools_list(tmp_path):
    responses = _run_server(
        [
            json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["result"]["serverInfo"]["name"] == "ue-knowledge-base"
    tools = responses[1]["result"]["tools"]
    assert tools[0]["name"] == "ue_kb_query"
    assert "query" in tools[0]["inputSchema"]["properties"]
    assert "raw_score" in tools[0]["description"]


def test_tools_call_returns_hits(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "ue_kb_query", "arguments": {"query": "movement speed"}},
        })],
        db,
        FakeEmbedder(),
    )
    call = responses[0]
    assert call["result"]["isError"] is False
    hits = json.loads(call["result"]["content"][0]["text"])
    assert hits and hits[0]["source"].startswith("ue-character-movement/")
    assert hits[0]["raw_score"] > 0
    assert hits[0]["rank"] == 1


def test_tools_call_missing_query_is_error(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "ue_kb_query", "arguments": {}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["result"]["isError"] is True


def test_tools_call_unknown_tool_is_error(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["result"]["isError"] is True


def test_unknown_method_returns_jsonrpc_error(tmp_path):
    responses = _run_server(
        [json.dumps({"jsonrpc": "2.0", "id": 6, "method": "resources/list"})],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["error"]["code"] == -32601


def test_notification_gets_no_response(tmp_path):
    stdout = io.StringIO()
    serve_loop(
        io.StringIO(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        ),
        stdout,
        chroma_dir=str(tmp_path / "db"),
        model_name="fake",
        embedder=FakeEmbedder(),
    )
    assert stdout.getvalue() == ""
