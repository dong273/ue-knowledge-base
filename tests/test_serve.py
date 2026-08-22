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
    assert "86 docs" not in tools[0]["description"]


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
    assert set(hits[0]) == {"source", "heading", "type", "score", "raw_score", "rank", "text"}
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
        [json.dumps({"jsonrpc": "2.0", "id": 6, "method": "prompts/list"})],
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


def test_tools_list_has_info_topics_glossary(tmp_path):
    responses = _run_server(
        [json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})],
        tmp_path / "db",
        FakeEmbedder(),
    )
    names = [tool["name"] for tool in responses[0]["result"]["tools"]]
    assert names == ["ue_kb_query", "ue_kb_info", "ue_kb_topics", "ue_kb_glossary"]


def test_info_tool_reports_missing_index(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "ue_kb_info", "arguments": {}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    call = responses[0]
    assert call["result"]["isError"] is False
    info = call["result"]["structuredContent"]
    assert info["index_ready"] is False
    assert info["topic_count"] >= 30
    assert "package_version" in info
    assert info["module_path"].endswith("__init__.py")
    assert info["model_matches"] is False
    assert set(info["corpus"]) == {"source", "sha256", "documents", "chunks", "stale"}


def test_info_tool_reports_ready_index(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {"name": "ue_kb_info", "arguments": {}},
        })],
        db,
        FakeEmbedder(),
    )
    info = responses[0]["result"]["structuredContent"]
    assert info["index_ready"] is True
    assert info["chunk_count"] >= 1
    assert info["generation"].startswith("gen-")


def test_info_tool_reports_package_and_corpus_identity(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 91, "method": "tools/call",
            "params": {"name": "ue_kb_info", "arguments": {}},
        })],
        db,
        FakeEmbedder(),
    )
    info = responses[0]["result"]["structuredContent"]
    assert info["module_path"].endswith("__init__.py")
    assert info["model_matches"] is True
    assert info["corpus"]["source"] == str(corpus.resolve())
    assert info["corpus"]["sha256"]
    assert info["corpus"]["documents"] == 1
    assert info["corpus"]["chunks"] == info["chunk_count"]
    assert info["corpus"]["stale"] is False


def test_topics_tool_lists_topics(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": {"name": "ue_kb_topics", "arguments": {}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    topics = responses[0]["result"]["structuredContent"]
    assert any(t["topic"] == "ue-gameplay-abilities" for t in topics)
    assert all("canonical" in t for t in topics)


def test_glossary_tool_filters_by_topic(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {"name": "ue_kb_glossary",
                       "arguments": {"topic": "ue-gameplay-abilities"}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    entries = responses[0]["result"]["structuredContent"]
    assert len(entries) == 1
    assert entries[0]["topic"] == "ue-gameplay-abilities"
    assert entries[0]["identifiers"]


def test_glossary_tool_unknown_topic_is_error(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 12, "method": "tools/call",
            "params": {"name": "ue_kb_glossary", "arguments": {"topic": "nope"}},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["result"]["isError"] is True


def test_resources_list_lists_topics(tmp_path):
    responses = _run_server(
        [json.dumps({"jsonrpc": "2.0", "id": 13, "method": "resources/list"})],
        tmp_path / "db",
        FakeEmbedder(),
    )
    resources = responses[0]["result"]["resources"]
    assert any(r["uri"] == "ue-kb://topic/ue-gameplay-abilities" for r in resources)


def test_resources_read_returns_skill_markdown(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 16, "method": "resources/read",
            "params": {"uri": "ue-kb://topic/ue-gameplay-abilities"},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    contents = responses[0]["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "ue-kb://topic/ue-gameplay-abilities"
    assert contents[0]["mimeType"] == "text/markdown"
    assert "Gameplay Ability System" in contents[0]["text"]


def test_resources_read_unknown_uri_is_error(tmp_path):
    responses = _run_server(
        [json.dumps({
            "jsonrpc": "2.0", "id": 17, "method": "resources/read",
            "params": {"uri": "ue-kb://topic/does-not-exist"},
        })],
        tmp_path / "db",
        FakeEmbedder(),
    )
    assert responses[0]["error"]["code"] == -32602


def test_repeated_query_hits_cache(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    responses = _run_server(
        [
            json.dumps({
                "jsonrpc": "2.0", "id": 14, "method": "tools/call",
                "params": {"name": "ue_kb_query",
                           "arguments": {"query": "movement speed"}},
            }),
            json.dumps({
                "jsonrpc": "2.0", "id": 15, "method": "tools/call",
                "params": {"name": "ue_kb_query",
                           "arguments": {"query": "movement speed"}},
            }),
        ],
        db,
        FakeEmbedder(),
    )
    assert responses[0]["result"]["structuredContent"] == responses[1]["result"]["structuredContent"]


def test_lazy_embedder_handshake_needs_no_model(tmp_path):
    # With embedder=None, initialize / tools/list / non-query tools must
    # answer WITHOUT loading the embedding model (lazy load, so the MCP
    # handshake stays inside client startup timeouts).
    stdin = io.StringIO("\n".join([
        json.dumps({
            "jsonrpc": "2.0", "id": 20, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }),
        json.dumps({"jsonrpc": "2.0", "id": 21, "method": "tools/list"}),
        json.dumps({
            "jsonrpc": "2.0", "id": 22, "method": "tools/call",
            "params": {"name": "ue_kb_topics", "arguments": {}},
        }),
    ]) + "\n")
    stdout = io.StringIO()
    serve_loop(
        stdin, stdout,
        chroma_dir=str(tmp_path / "db"),
        model_name="fake",
        embedder=None,  # no model provided; must never be loaded here
        top_k=3,
    )
    responses = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
    assert len(responses) == 3
    assert responses[0]["result"]["serverInfo"]["name"] == "ue-knowledge-base"
    assert responses[1]["result"]["tools"][0]["name"] == "ue_kb_query"
    assert responses[2]["result"]["isError"] is False
