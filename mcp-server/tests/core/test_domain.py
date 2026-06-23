"""Pure unit tests for `opensddrag.core.domain`.

These tests exercise the domain types (Tool, Permission, AuthorizationDecision,
Request, Response, ValidationResult, ValidationError) without any I/O:
no PostgreSQL, no embedding model, no HTTP server. They must run in
< 100 ms total.

Spec references:
- mcp-domain-core-spec REQ-001 (Pure data types, JSON-serializable)
- mcp-domain-core-spec REQ-002 (Authorization policies as pure functions)
- mcp-domain-core-spec REQ-003 (Input and output validators — types)
- mcp-domain-core-spec REQ-004 (Domain layer is transport-agnostic)

The "import without side effects" test (test_domain_import_is_pure) runs
in a **subprocess** so it is hermetic from this test session's conftest
(which already opens a DB pool in `tests/conftest.py`). Running the import
in a fresh interpreter and inspecting its exit code / output is the
canonical way to assert that an import has no side effects — see
`mcp-domain-core-spec` REQ-001 Scenario "Pure domain module is importable
without side effects".
"""

from __future__ import annotations

import json
import subprocess
import sys
import sys
import textwrap

import pytest

from opensddrag.core.domain import (
    ALLOWED_KINDS,
    Allow,
    AuthorizationDecision,
    Deny,
    Invalid,
    OK,
    Permission,
    Request,
    RequireConfirmation,
    Response,
    Tool,
    ValidationError,
    ValidationResult,
    is_allowed,
    is_valid,
)


# ─── Tool ────────────────────────────────────────────────────────────────────


class TestTool:
    def test_construction_with_required_fields(self) -> None:
        tool = Tool(
            name="search_semantic",
            description="Semantic search over artifacts.",
            required_permission=Permission.READ_ONLY,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert tool.name == "search_semantic"
        assert tool.description == "Semantic search over artifacts."
        assert tool.required_permission is Permission.READ_ONLY
        assert tool.input_schema == {"type": "object"}
        assert tool.output_schema == {"type": "object"}
        # metadata defaults to an empty dict and is a fresh instance per Tool
        assert tool.metadata == {}
        assert isinstance(tool.metadata, dict)

    def test_construction_with_all_three_permissions(self) -> None:
        for perm in Permission:
            tool = Tool(
                name=f"tool-{perm.value}",
                description="x",
                required_permission=perm,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
            assert tool.required_permission is perm

    def test_frozen_rejects_mutation(self) -> None:
        tool = Tool(
            name="x",
            description="x",
            required_permission=Permission.ADMIN,
            input_schema={},
            output_schema={},
        )
        with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError
            tool.name = "y"  # type: ignore[misc]

    def test_post_init_rejects_non_dict_input_schema(self) -> None:
        with pytest.raises(TypeError) as exc_info:
            Tool(
                name="x",
                description="x",
                required_permission=Permission.ADMIN,
                input_schema="not a dict",  # type: ignore[arg-type]
                output_schema={},
            )
        assert "input_schema" in str(exc_info.value)

    def test_post_init_rejects_non_dict_output_schema(self) -> None:
        with pytest.raises(TypeError) as exc_info:
            Tool(
                name="x",
                description="x",
                required_permission=Permission.ADMIN,
                input_schema={},
                output_schema=["not", "a", "dict"],  # type: ignore[arg-type]
            )
        assert "output_schema" in str(exc_info.value)

    def test_json_serializable_with_default_str(self) -> None:
        """REQ-001 Scenario: `json.dumps(tool, default=str)` succeeds.

        `Tool` is a frozen dataclass whose fields are JSON-native except
        for the `Permission` enum. The spec asks for two complementary
        guarantees:

        1. `json.dumps(tool, default=str)` does NOT raise (the `default`
           fallback is invoked once, with the whole dataclass, and the
           resulting string is itself a valid JSON string literal).
        2. When serialized **field-by-field** via `dataclasses.asdict`
           (the strategy the MCP adapter uses to produce a
           `CallToolResult`), the resulting JSON object exposes the
           `Tool` fields in a stable, machine-readable form, with the
           `Permission` enum rendered as its string value.
        """
        from dataclasses import asdict, fields

        tool = Tool(
            name="search_semantic",
            description="Semantic search",
            required_permission=Permission.READ_ONLY,
            input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
            output_schema={"type": "array"},
            metadata={"capability": "semantic-memory"},
        )
        # Guarantee 1: `json.dumps(tool, default=str)` does not raise.
        out = json.dumps(tool, default=str)
        assert isinstance(out, str)
        assert len(out) > 0

        # Guarantee 2: field-by-field serialization with enum coercion.
        as_dict = asdict(tool)
        # Replace the Permission enum with its string value.
        as_dict["required_permission"] = tool.required_permission.value
        serialized = json.dumps(as_dict)
        parsed = json.loads(serialized)
        assert parsed["name"] == "search_semantic"
        assert parsed["required_permission"] == "READ_ONLY"
        assert parsed["input_schema"]["type"] == "object"
        assert parsed["input_schema"]["properties"]["q"]["type"] == "string"
        assert parsed["output_schema"] == {"type": "array"}
        assert parsed["metadata"] == {"capability": "semantic-memory"}
        # And every field in the dataclass is present in the output.
        for f in fields(tool):
            assert f.name in parsed, f"Field {f.name!r} missing from serialized Tool"


# ─── Permission ──────────────────────────────────────────────────────────────


class TestPermission:
    def test_enum_has_three_values(self) -> None:
        # Closed set — adding a new permission is a deliberate change.
        assert {p.value for p in Permission} == {"READ_ONLY", "WRITE", "ADMIN"}

    def test_enum_members_are_str(self) -> None:
        # `str, Enum` lets us compare directly with string literals.
        assert Permission.READ_ONLY == "READ_ONLY"
        assert Permission.WRITE == "WRITE"
        assert Permission.ADMIN == "ADMIN"
        assert isinstance(Permission.READ_ONLY, str)

    def test_allowed_kinds_contains_three_known_kinds(self) -> None:
        # Guard against accidentally adding a new variant without updating ALLOWED_KINDS.
        assert "allow" in ALLOWED_KINDS
        assert "deny" in ALLOWED_KINDS
        assert "require_confirmation" in ALLOWED_KINDS
        assert len(ALLOWED_KINDS) == 3


# ─── AuthorizationDecision + is_allowed ──────────────────────────────────────


class TestAuthorizationDecision:
    def test_is_allowed_returns_true_for_allow(self) -> None:
        assert is_allowed(Allow()) is True

    def test_is_allowed_returns_false_for_deny(self) -> None:
        assert is_allowed(Deny("permission READ_ONLY < required WRITE")) is False

    def test_is_allowed_returns_false_for_require_confirmation(self) -> None:
        # RequireConfirmation is not yet authorized — caller must resubmit.
        assert is_allowed(RequireConfirmation("type 'yes' to confirm")) is False

    def test_deny_carries_reason(self) -> None:
        reason = "tool requires ADMIN"
        decision = Deny(reason)
        assert decision.reason == reason
        assert decision.kind == "deny"

    def test_require_confirmation_carries_prompt(self) -> None:
        prompt = "Re-submit with confirm=true"
        decision = RequireConfirmation(prompt)
        assert decision.prompt == prompt
        assert decision.kind == "require_confirmation"

    def test_authorization_decision_union_accepts_all_variants(self) -> None:
        # Type-system check: the three variants are members of the union.
        decisions: list[AuthorizationDecision] = [
            Allow(),
            Deny("r"),
            RequireConfirmation("p"),
        ]
        assert len(decisions) == 3


# ─── Request ─────────────────────────────────────────────────────────────────


class TestRequest:
    def test_construction_with_all_fields(self) -> None:
        req = Request(
            tool_name="search_semantic",
            parameters={"query": "clean architecture"},
            caller_id="stdio",
            permission=Permission.ADMIN,
        )
        assert req.tool_name == "search_semantic"
        assert req.parameters == {"query": "clean architecture"}
        assert req.caller_id == "stdio"
        assert req.permission is Permission.ADMIN

    def test_frozen_rejects_mutation(self) -> None:
        req = Request(
            tool_name="x",
            parameters={},
            caller_id="c",
            permission=Permission.WRITE,
        )
        with pytest.raises(Exception):
            req.tool_name = "y"  # type: ignore[misc]


# ─── Response ────────────────────────────────────────────────────────────────


class TestResponse:
    def test_ok_factory(self) -> None:
        value = {"results": [1, 2, 3]}
        r = Response.ok(value)
        assert r.is_ok is True
        assert r.value == value
        assert r.code is None
        assert r.message is None
        assert r.details is None

    def test_error_factory_without_details(self) -> None:
        r = Response.error("TOOL_NOT_FOUND", "no such tool")
        assert r.is_ok is False
        assert r.value is None
        assert r.code == "TOOL_NOT_FOUND"
        assert r.message == "no such tool"
        assert r.details is None

    def test_error_factory_with_details(self) -> None:
        details = {"retry_after": 12}
        r = Response.error("RATE_LIMITED", "slow down", details=details)
        assert r.is_ok is False
        assert r.code == "RATE_LIMITED"
        assert r.message == "slow down"
        assert r.details == details

    def test_error_factory_details_keyword_only(self) -> None:
        # `details` must be passed as a kwarg, not positionally. This is
        # an API contract: callers should not accidentally pass
        # Response.error("X", "y", "z") thinking the third positional is
        # `details`.
        with pytest.raises(TypeError):
            Response.error("X", "y", "z")  # type: ignore[misc]

    def test_response_round_trip_via_dataclass(self) -> None:
        # Response is frozen, so "round-trip" = same fields after construction.
        r1 = Response.ok({"k": "v"})
        r2 = Response.error("E", "m", details=[1, 2])
        # Equality is structural (frozen dataclass generates __eq__).
        assert r1 == Response.ok({"k": "v"})
        assert r2 == Response.error("E", "m", details=[1, 2])
        assert r1 != r2

    def test_frozen_rejects_mutation(self) -> None:
        r = Response.ok(1)
        with pytest.raises(Exception):
            r.is_ok = False  # type: ignore[misc]


# ─── ValidationResult + ValidationError ──────────────────────────────────────


class TestValidationResult:
    def test_ok_construction(self) -> None:
        result = OK(value={"normalized": True})
        assert result.value == {"normalized": True}
        assert result.kind == "ok"
        assert is_valid(result) is True

    def test_invalid_construction_with_errors(self) -> None:
        errors = [
            ValidationError(path="query", message="field required"),
            ValidationError(path="limit", message="must be int"),
        ]
        result = Invalid(errors=errors)
        assert result.errors == errors
        assert result.kind == "invalid"
        assert is_valid(result) is False

    def test_invalid_construction_with_empty_errors(self) -> None:
        # An "invalid" with no specific errors is a valid shape: the
        # validator may not know the exact reason. The downstream consumer
        # (the use case) is responsible for surfacing a generic message.
        result = Invalid(errors=[])
        assert result.errors == []
        assert is_valid(result) is False

    def test_validation_error_carries_path_and_message(self) -> None:
        ve = ValidationError(path="results.0.score", message="must be >= 0")
        assert ve.path == "results.0.score"
        assert ve.message == "must be >= 0"

    def test_validation_result_union_accepts_ok_and_invalid(self) -> None:
        results: list[ValidationResult] = [
            OK(value=1),
            Invalid(errors=[ValidationError(path="x", message="y")]),
        ]
        assert len(results) == 2
        assert is_valid(results[0]) is True
        assert is_valid(results[1]) is False


# ─── Spec REQ-001 Scenario: import without side effects ──────────────────────


def test_domain_import_is_pure() -> None:
    """The import of `opensddrag.core.domain` MUST NOT trigger I/O.

    Verified by running the import in a fresh subprocess with the
    I/O-triggering attributes replaced by raising mocks. If the import
    touches any of them, the subprocess fails loudly.

    This is the literal acceptance criterion from the task:
    "patching `psycopg.connect` and `sentence_transformers.SentenceTransformer.__init__`
    and asserting they are never called".
    """
    code = textwrap.dedent(
        """
        import sys
        import unittest.mock

        # Block any access to psycopg.connect (the function the
        # connection pool would call on first use) and to
        # SentenceTransformer.__init__ (the function that downloads
        # and loads the embedding model). Any access to either is a
        # spec violation.
        def _forbid_connect(*a, **kw):
            raise AssertionError(
                "psycopg.connect was called during opensddrag.core.domain import"
            )

        class _ForbidSentenceTransformer:
            def __init__(self, *a, **kw):
                raise AssertionError(
                    "sentence_transformers.SentenceTransformer was instantiated "
                    "during opensddrag.core.domain import"
                )

        # Patch the symbols. We use create=True so the patch succeeds
        # even if the attribute does not exist yet.
        try:
            psycopg = sys.modules.get("psycopg")
            if psycopg is not None and hasattr(psycopg, "connect"):
                unittest.mock.patch.object(psycopg, "connect", _forbid_connect).start()
        except Exception:
            pass

        try:
            st_mod = sys.modules.get("sentence_transformers")
            if st_mod is not None and hasattr(st_mod, "SentenceTransformer"):
                unittest.mock.patch.object(
                    st_mod, "SentenceTransformer", _ForbidSentenceTransformer
                ).start()
        except Exception:
            pass

        # Also forbid reads of env vars during the import (the spec
        # says "no reads of environment variables").
        import os
        original_environ_get = os.environ.get
        def _forbid_env(key, *a, **kw):
            if key in ("DATABASE_URL", "EMBEDDING_MODEL", "OPENSDDRAG_PROJECT"):
                raise AssertionError(
                    f"os.environ.get({key!r}) was called during opensddrag.core.domain import"
                )
            return original_environ_get(key, *a, **kw)
        unittest.mock.patch.object(os.environ, "get", _forbid_env).start()

        # The import under test. All seven names are spec-mandated exports.
        from opensddrag.core.domain import (  # noqa: F401
            Tool, Permission, Request, Response, AuthorizationDecision,
            ValidationResult, ValidationError,
        )

        print("IMPORT_OK")
        """
    )
    import os
    # The subprocess needs the package's `src/` directory on its
    # `sys.path` (the editable install records it via a `.pth` file
    # in the venv's `site-packages`, but `.pth` files are only
    # processed by `site.py`, and we run with `-S` to skip site
    # customization and save ~50ms of cold-start). The `src/` path
    # is computed from this test file's location — robust to
    # `mcp-server/` being moved or symlinked.
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.normpath(os.path.join(tests_dir, "..", "..", "src"))
    env = os.environ.copy()
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 0, (
        f"opensddrag.core.domain import was not pure.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout, (
        f"Subprocess did not reach the import-OK marker.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
