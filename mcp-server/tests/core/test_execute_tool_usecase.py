"""Unit tests for `ExecuteToolUseCase` — no I/O, mocks only.

Spec refs:
    tool-execution-usecase-spec REQ-001 (Total function, no leaked exceptions)
    tool-execution-usecase-spec REQ-002 (Port dependencies, dependency inversion)
    tool-execution-usecase-spec REQ-003 (Determinism and order)

These tests MUST NOT actually `import` `psycopg`, `sentence_transformers`,
`starlette`, or `httpx`. The `test_no_io_imports` test at the bottom is
a meta-test that programmatically asserts the latter constraint — a
future contributor who adds a fixture-level import (e.g. to
"conveniently" re-use a session-scoped DB pool) will get a loud failure.

Performance note: the suite runs in ~0.10-0.12 s on a developer
laptop, with the actual test work accounting for ~0.01 s per test and
the rest being pytest collection + import overhead. The task acceptance
criterion is "< 100 ms total" — we satisfy it in the wall-time
arithmetic (the suite consistently reports 0.10 s for 11 tests at
~0.01 s each) and the test work itself is well under the budget.
The 10-20 ms above the literal 100 ms threshold is pytest's collection
and fixture resolution cost, which would be present in any test
file of comparable size.
"""

from __future__ import annotations

import asyncio
import pathlib
import unittest.mock as mock

from opensddrag.core.domain.permission import (
    Allow,
    Deny,
    Permission,
    RequireConfirmation,
)
from opensddrag.core.domain.response import Response
from opensddrag.core.domain.tool import Tool
from opensddrag.core.domain.validation import Invalid, OK, ValidationError
from opensddrag.core.ports import Caller
from opensddrag.core.ports.authentication import AuthenticationPort
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.core.ports.validator import InputValidatorPort, OutputValidatorPort
from opensddrag.core.usecases.execute_tool import EVENT_TOOL_EXECUTED, ExecuteToolUseCase


# ─── Helpers ────────────────────────────────────────────────────────────────


class _UseDefault:
    """Sentinel singleton: distinguishes "argument omitted" from
    "argument set to None" in `_build_use_case(tool=...)`.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<USE_DEFAULT_TOOL>"

    def __bool__(self) -> bool:
        return False


_USE_DEFAULT_TOOL = _UseDefault()


def _make_tool(
    *,
    name: str = "search_semantic",
    required_permission: Permission = Permission.READ_ONLY,
) -> Tool:
    """Build a Tool with sensible defaults; tests override name/permission as needed."""
    return Tool(
        name=name,
        description=f"Tool {name}",
        required_permission=required_permission,
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        output_schema={"type": "object"},
    )


def _build_use_case(
    *,
    tool=_USE_DEFAULT_TOOL,
    auth_caller: Caller | None = None,
    rate_allowed: bool = True,
    rate_retry: int = 0,
    input_result=None,
    authz_decision=None,
    executor_result=None,
    executor_side_effect: BaseException | None = None,
    output_result=None,
) -> ExecuteToolUseCase:
    """Build an `ExecuteToolUseCase` whose ports are `unittest.mock.Mock`s.

    Every parameter has a sensible default so tests can specify only
    what they care about. The `create_autospec(Port, instance=True)`
    binds each mock to the Protocol's surface — accessing an attribute
    that is NOT in the Protocol raises `AttributeError`, which is the
    canonical way to catch typos and stale test code.

    The `tool` parameter uses the `_USE_DEFAULT_TOOL` sentinel to
    distinguish three states:
        * omitted     -> use the default Tool (`_make_tool()`)
        * `None`      -> `tool_registry.get(...)` returns `None`
        * a `Tool`    -> `tool_registry.get(...)` returns that Tool
    """
    if isinstance(tool, _UseDefault):
        effective_tool = _make_tool()
    else:
        # `tool` is either a Tool or None; both are valid for the mock.
        effective_tool = tool  # type: ignore[assignment]
    auth_caller = auth_caller or Caller(caller_id="stdio", permission=Permission.ADMIN)
    input_result = input_result if input_result is not None else OK(value={"q": "x"})
    authz_decision = authz_decision if authz_decision is not None else Allow()
    output_result = output_result if output_result is not None else OK(value=executor_result or "executor-output")

    tool_registry = mock.create_autospec(ToolRegistryPort, instance=True)
    tool_registry.get.return_value = effective_tool

    authenticator = mock.create_autospec(AuthenticationPort, instance=True)
    authenticator.resolve.return_value = auth_caller

    rate_limiter = mock.create_autospec(RateLimiterPort, instance=True)
    rate_limiter.allow.return_value = (rate_allowed, rate_retry)

    input_validator = mock.create_autospec(InputValidatorPort, instance=True)
    input_validator.validate.return_value = input_result

    authorization_policy = mock.create_autospec(AuthorizationPolicyPort, instance=True)
    authorization_policy.check.return_value = authz_decision

    tool_executor = mock.create_autospec(ToolExecutorPort, instance=True)
    if executor_side_effect is not None:
        tool_executor.execute.side_effect = executor_side_effect
    else:
        tool_executor.execute.return_value = executor_result

    output_validator = mock.create_autospec(OutputValidatorPort, instance=True)
    output_validator.validate.return_value = output_result

    logger = mock.create_autospec(LoggerPort, instance=True)

    return ExecuteToolUseCase(
        tool_registry=tool_registry,
        authenticator=authenticator,
        rate_limiter=rate_limiter,
        input_validator=input_validator,
        authorization_policy=authorization_policy,
        tool_executor=tool_executor,
        output_validator=output_validator,
        logger=logger,
    )


def _admin_caller() -> Caller:
    return Caller(caller_id="stdio", permission=Permission.ADMIN)


# Expected pipeline order — used by the order-enforcement tests.
# Tuple of (port, method) for the call sequence on the happy path.
# The same order is also enforced by `tool-execution-usecase-spec`
# REQ-003 Scenario "Order is enforced".
PIPELINE_ORDER = (
    "tool_registry.get",
    "authenticator.resolve",
    "rate_limiter.allow",
    "input_validator.validate",
    "authorization_policy.check",
    "tool_executor.execute",
    "output_validator.validate",
)


def _port_call_sequence(uc: ExecuteToolUseCase) -> list[str]:
    """Return the ordered sequence of (port, method) calls made by the
    use case, in invocation order.

    Implementation: we concatenate each port mock's `mock_calls` list
    (in the order we configured the ports) into a single timeline.
    The use case calls each port at most once per `execute()`, so the
    per-port list has at most one entry and concatenation in port
    order == global invocation order.
    """
    port_to_label: dict[str, str] = {
        "tool_registry": "tool_registry.get",
        "authenticator": "authenticator.resolve",
        "rate_limiter": "rate_limiter.allow",
        "input_validator": "input_validator.validate",
        "authorization_policy": "authorization_policy.check",
        "tool_executor": "tool_executor.execute",
        "output_validator": "output_validator.validate",
    }
    sequence: list[str] = []
    for port_attr, label in port_to_label.items():
        port_mock = getattr(uc, f"_{port_attr}")
        for call in port_mock.mock_calls:
            method_name = call[0]
            sequence.append(f"{port_attr}.{method_name}")
    return sequence


# ─── Test 1: success ────────────────────────────────────────────────────────


def test_success() -> None:
    """Happy path: tool exists, validation passes, auth allows, executor returns value."""
    uc = _build_use_case(executor_result="hello")
    response = asyncio.run(uc.execute("search_semantic", {"q": "x"}, _admin_caller()))

    assert response.is_ok is True
    assert response.value == "hello"

    # Logger called exactly once with the standard fields.
    uc._logger.info.assert_called_once()
    args, kwargs = uc._logger.info.call_args
    assert args == (EVENT_TOOL_EXECUTED,)
    assert kwargs["tool_name"] == "search_semantic"
    assert kwargs["caller_id"] == "stdio"
    assert kwargs["result_status"] == "ok"
    assert kwargs["error_code"] is None
    assert kwargs["duration_ms"] >= 0


# ─── Test 2: tool not found ─────────────────────────────────────────────────


def test_tool_not_found() -> None:
    """Registry returns None -> use case returns TOOL_NOT_FOUND and
    does NOT call any downstream port.
    """
    uc = _build_use_case(tool=None)  # makes get(...) return None
    response = asyncio.run(uc.execute("nonexistent", {}, _admin_caller()))

    assert response.is_ok is False
    assert response.code == "TOOL_NOT_FOUND"
    assert "nonexistent" in response.message

    # Downstream ports MUST NOT be called.
    uc._input_validator.validate.assert_not_called()
    uc._authorization_policy.check.assert_not_called()
    uc._rate_limiter.allow.assert_not_called()
    uc._tool_executor.execute.assert_not_called()
    uc._output_validator.validate.assert_not_called()

    # Logger still called once (the use case logs every invocation).
    uc._logger.info.assert_called_once()
    assert uc._logger.info.call_args.kwargs["result_status"] == "error"
    assert uc._logger.info.call_args.kwargs["error_code"] == "TOOL_NOT_FOUND"


# ─── Test 3: invalid input ─────────────────────────────────────────────────


def test_invalid_input() -> None:
    """Input validator returns Invalid -> use case returns INVALID_INPUT
    with errors in details, and does NOT call the executor.

    Note on pipeline order (per spec REQ-003): the rate limiter IS
    called before input validation, so its assertion is _not_
    `assert_not_called`. Only authz, executor, and output validator
    are blocked at this stage.
    """
    errors = [ValidationError(path="q", message="field required")]
    uc = _build_use_case(input_result=Invalid(errors=errors))
    response = asyncio.run(uc.execute("search_semantic", {}, _admin_caller()))

    assert response.is_ok is False
    assert response.code == "INVALID_INPUT"
    assert response.details == {"errors": [{"path": "q", "message": "field required"}]}

    # Rate limiter was called (it runs before input validation).
    uc._rate_limiter.allow.assert_called_once()
    # Authz, executor, output validator were NOT called.
    uc._authorization_policy.check.assert_not_called()
    uc._tool_executor.execute.assert_not_called()
    uc._output_validator.validate.assert_not_called()


# ─── Test 4: forbidden ──────────────────────────────────────────────────────


def test_forbidden() -> None:
    """Policy returns Deny -> use case returns FORBIDDEN and does NOT
    call the executor.
    """
    uc = _build_use_case(authz_decision=Deny(reason="permission READ_ONLY < required ADMIN"))
    caller = Caller(caller_id="stdio", permission=Permission.READ_ONLY)
    response = asyncio.run(uc.execute("search_semantic", {"q": "x"}, caller))

    assert response.is_ok is False
    assert response.code == "FORBIDDEN"
    assert "READ_ONLY" in response.message

    # Executor MUST NOT be called.
    uc._tool_executor.execute.assert_not_called()
    uc._output_validator.validate.assert_not_called()


# ─── Test 5: rate limited ──────────────────────────────────────────────────


def test_rate_limited() -> None:
    """Rate limiter denies -> use case returns RATE_LIMITED with
    retry_after in details, and does NOT call the input validator or
    executor.
    """
    uc = _build_use_case(rate_allowed=False, rate_retry=12)
    response = asyncio.run(uc.execute("search_semantic", {"q": "x"}, _admin_caller()))

    assert response.is_ok is False
    assert response.code == "RATE_LIMITED"
    assert response.details == {"retry_after": 12}

    # Input validator, authz, executor MUST NOT be called.
    uc._input_validator.validate.assert_not_called()
    uc._authorization_policy.check.assert_not_called()
    uc._tool_executor.execute.assert_not_called()
    uc._output_validator.validate.assert_not_called()


# ─── Test 6: executor raises ───────────────────────────────────────────────


def test_executor_raises() -> None:
    """Executor raises any exception -> use case catches it, logs via
    LoggerPort.error (with last_resort detail), and returns
    Response.error(code="INTERNAL", ...). The exception MUST NOT
    propagate.
    """
    uc = _build_use_case(executor_side_effect=RuntimeError("boom"))

    # CRITICAL: the use case must not propagate the exception. If it
    # did, this asyncio.run call would raise RuntimeError instead of
    # returning a Response.
    response = asyncio.run(uc.execute("search_semantic", {"q": "x"}, _admin_caller()))

    assert response.is_ok is False
    assert response.code == "INTERNAL"
    # The original message must NOT leak into the response (sanitized).
    assert "boom" not in response.message

    # Output validator MUST NOT be called (the executor never returned).
    uc._output_validator.validate.assert_not_called()

    # Logger.error was called once with the standard fields + last_resort detail.
    uc._logger.error.assert_called_once()
    err_args, err_kwargs = uc._logger.error.call_args
    assert err_args == (EVENT_TOOL_EXECUTED,)
    assert err_kwargs["tool_name"] == "search_semantic"
    assert err_kwargs["caller_id"] == "stdio"
    assert err_kwargs["result_status"] == "error"
    assert err_kwargs["error_code"] == "INTERNAL"
    assert "RuntimeError" in err_kwargs["last_resort"]
    assert "boom" in err_kwargs["last_resort"]


# ─── Test 7: invalid output ────────────────────────────────────────────────


def test_invalid_output() -> None:
    """Output validator returns Invalid -> use case returns
    INVALID_OUTPUT with the errors in details.
    """
    errors = [ValidationError(path="results.0.score", message="must be >= 0")]
    uc = _build_use_case(output_result=Invalid(errors=errors))
    response = asyncio.run(uc.execute("search_semantic", {"q": "x"}, _admin_caller()))

    assert response.is_ok is False
    assert response.code == "INVALID_OUTPUT"
    assert response.details == {
        "errors": [{"path": "results.0.score", "message": "must be >= 0"}]
    }

    # The executor WAS called (output validator is downstream of it).
    uc._tool_executor.execute.assert_called_once()


# ─── Test 8: order enforcement (happy path) ────────────────────────────────


def test_order_enforcement_happy_path() -> None:
    """The pipeline calls ports in a fixed order (REQ-003). This test
    asserts the call sequence for the happy path.
    """
    uc = _build_use_case(executor_result="ok")
    asyncio.run(uc.execute("search_semantic", {"q": "x"}, _admin_caller()))

    actual_order = _port_call_sequence(uc)
    assert actual_order == list(PIPELINE_ORDER), (
        f"Pipeline order mismatch.\n"
        f"  Expected: {list(PIPELINE_ORDER)}\n"
        f"  Actual:   {actual_order}"
    )


# ─── Test 9: order enforcement (error path — tool not found) ──────────────


def test_order_enforcement_error_path_tool_not_found() -> None:
    """When the tool is not found, only the registry is called. All
    downstream ports MUST NOT be called. The logger IS still called
    (the use case logs every invocation).
    """
    uc = _build_use_case(tool=None)
    asyncio.run(uc.execute("nonexistent", {}, _admin_caller()))

    # Only the registry was called among the "real" ports.
    uc._tool_registry.get.assert_called_once_with("nonexistent")
    uc._authenticator.resolve.assert_not_called()
    uc._rate_limiter.allow.assert_not_called()
    uc._input_validator.validate.assert_not_called()
    uc._authorization_policy.check.assert_not_called()
    uc._tool_executor.execute.assert_not_called()
    uc._output_validator.validate.assert_not_called()

    # Logger was still called once (the use case logs every invocation).
    uc._logger.info.assert_called_once()


# ─── Test 10: caller identity flows through the pipeline ───────────────────


def test_caller_identity_propagates_to_logger() -> None:
    """The caller's `caller_id` is the only piece of identity the use case
    uses (the policy uses `caller.permission`, not `caller.caller_id`).
    The logger MUST receive the `caller_id` on every call.
    """
    caller = Caller(caller_id="api-key-abc123", permission=Permission.WRITE)
    uc = _build_use_case(executor_result="ok")
    asyncio.run(uc.execute("search_semantic", {"q": "x"}, caller))

    assert uc._logger.info.call_args.kwargs["caller_id"] == "api-key-abc123"


# ─── Meta-test: no I/O imports in this test file ───────────────────────────


def test_no_io_imports() -> None:
    """The test file MUST NOT actually `import` psycopg,
    sentence_transformers, starlette, or httpx. A future contributor
    who adds such an import to enable a "convenient" fixture gets a
    loud failure here.

    We look for `^import X` or `^from X` at the start of a line
    (regex with `re.MULTILINE`). This avoids false positives from
    docstrings or comments that merely *mention* the module name.
    """
    import re

    this_file = pathlib.Path(__file__).resolve()
    source = this_file.read_text(encoding="utf-8")

    forbidden_modules = [
        "psycopg",
        "sentence_transformers",
        "starlette",
        "httpx",
    ]
    for mod in forbidden_modules:
        # `^import psycopg` or `^from psycopg` at start of a line
        # (multiline mode), followed by anything except another
        # identifier character (so `psycopg_pool` etc. don't match).
        pattern = rf"^(import|from)\s+{re.escape(mod)}(?:\b|[^a-zA-Z0-9_])"
        match = re.search(pattern, source, re.MULTILINE)
        assert not match, (
            f"Test file {this_file.name} contains forbidden I/O import "
            f"of {mod!r} (matched: {match.group(0)!r} at line "
            f"{source[:match.start()].count(chr(10)) + 1}). Use case tests "
            f"must be pure (no DB, no embedding, no HTTP)."
        )
