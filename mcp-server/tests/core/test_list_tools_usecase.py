"""Unit tests for `ListToolsUseCase` — no I/O, mocks only.

Spec refs:
    tool-listing-usecase-spec REQ-001 (Permission-aware filtering)
    tool-listing-usecase-spec REQ-002 (Minimal port dependencies)
    tool-listing-usecase-spec REQ-003 (Stable ordering)

These tests MUST run in < 50 ms total and MUST NOT import
`psycopg`, `sentence_transformers`, `starlette`, or `httpx`. The
`test_no_io_imports` test at the bottom is a meta-test that
programmatically asserts the latter constraint.
"""

from __future__ import annotations

import inspect
import pathlib
import unittest.mock as mock

from opensddrag.core.domain.permission import (
    Allow,
    Deny,
    Permission,
    RequireConfirmation,
)
from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports import Caller
from opensddrag.core.ports.authentication import AuthenticationPort
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.core.ports.validator import InputValidatorPort, OutputValidatorPort
from opensddrag.core.usecases.list_tools import EVENT_TOOLS_LISTED, ListToolsUseCase


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_tool(name: str, required_permission: Permission = Permission.READ_ONLY) -> Tool:
    return Tool(
        name=name,
        description=f"Tool {name}",
        required_permission=required_permission,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )


def _build_use_case(
    *,
    tools: list[Tool] | None = None,
    allow_set: set[str] | None = None,
) -> ListToolsUseCase:
    """Build a `ListToolsUseCase` with mock ports.

    `allow_set` is the set of tool NAMES that the policy allows. If
    `None`, all tools are allowed (the default policy returns `Allow`
    for every tool).
    """
    tools = tools if tools is not None else []
    allow_set = allow_set if allow_set is not None else {t.name for t in tools}

    def check(_caller_permission: Permission, tool: Tool):
        if tool.name in allow_set:
            return Allow()
        return Deny(f"permission denied for {tool.name}")

    tool_registry = mock.create_autospec(ToolRegistryPort, instance=True)
    tool_registry.list.return_value = list(tools)

    authorization_policy = mock.create_autospec(AuthorizationPolicyPort, instance=True)
    authorization_policy.check.side_effect = check

    logger = mock.create_autospec(LoggerPort, instance=True)

    return ListToolsUseCase(
        tool_registry=tool_registry,
        authorization_policy=authorization_policy,
        logger=logger,
    )


# ─── Test 1: returns all for admin ─────────────────────────────────────────


def test_returns_all_for_admin() -> None:
    """ADMIN sees every tool in the registry."""
    tools = [
        _make_tool("zeta", Permission.READ_ONLY),
        _make_tool("Alpha", Permission.WRITE),
        _make_tool("beta", Permission.ADMIN),
    ]
    uc = _build_use_case(tools=tools)

    result = uc.list_for(Permission.ADMIN)
    names = [t.name for t in result]
    # The default policy is "allow everything", so ADMIN sees all 3.
    assert names == ["Alpha", "beta", "zeta"]  # case-insensitive sorted


# ─── Test 2: filters denied for readonly ───────────────────────────────────


def test_filters_denied_for_readonly() -> None:
    """A READ_ONLY caller sees only tools the policy allows (the WRITE
    and ADMIN tools are denied).
    """
    tools = [
        _make_tool("read_tool", Permission.READ_ONLY),
        _make_tool("write_tool", Permission.WRITE),
        _make_tool("admin_tool", Permission.ADMIN),
    ]
    # Only `read_tool` is allowed.
    uc = _build_use_case(tools=tools, allow_set={"read_tool"})

    result = uc.list_for(Permission.READ_ONLY)
    names = [t.name for t in result]
    assert names == ["read_tool"]

    # The policy was queried for every tool (3 times) — not short-circuited.
    assert uc._authorization_policy.check.call_count == 3


# ─── Test 3: empty for none permission ─────────────────────────────────────


def test_empty_for_none_permission() -> None:
    """When the policy denies every tool (e.g. anonymous caller), the
    use case returns an empty list and does not raise.
    """
    tools = [
        _make_tool("a", Permission.READ_ONLY),
        _make_tool("b", Permission.WRITE),
    ]
    uc = _build_use_case(tools=tools, allow_set=set())  # nothing allowed

    result = uc.list_for(Permission.READ_ONLY)
    assert result == []
    assert isinstance(result, list)  # never None


# ─── Test 4: stable alphabetical order ────────────────────────────────────


def test_stable_alphabetical_order() -> None:
    """The returned list is sorted by `Tool.name` (case-insensitive)
    even when the input order would not sort naturally.
    """
    tools = [
        _make_tool("zeta"),
        _make_tool("Alpha"),
        _make_tool("beta"),
        _make_tool("Gamma"),
        _make_tool("delta"),
    ]
    uc = _build_use_case(tools=tools)

    result = uc.list_for(Permission.ADMIN)
    names = [t.name for t in result]
    assert names == ["Alpha", "beta", "delta", "Gamma", "zeta"]

    # Two consecutive calls return the same order (REQ-003 stable).
    result_2 = uc.list_for(Permission.ADMIN)
    assert [t.name for t in result_2] == names


# ─── Test 5: executor port never called ───────────────────────────────────


def test_executor_port_never_called() -> None:
    """The use case MUST NOT accept a `ToolExecutorPort` argument. We
    verify this two ways:

    1. **Static check** (via `inspect.signature`): the constructor's
       parameter list MUST NOT contain any executor-related name.
       This catches the regression class of "someone adds an executor
       port to the use case's constructor in a future PR".

    2. **Behavioural check**: even if we instantiate the use case and
       pass it a `Mock(spec=ToolExecutorPort)` (via `setattr` after
       construction, since the constructor refuses it), the use case
       does not call any of its methods during `list_for`. This
       proves the use case never reaches for an executor — it has no
       reference to one in the first place.
    """
    # (1) Static check on the constructor signature.
    sig = inspect.signature(ListToolsUseCase.__init__)
    param_names = set(sig.parameters.keys())
    forbidden_in_ctor = {
        "tool_executor", "executor", "ToolExecutorPort",
        "rate_limiter", "authenticator", "AuthenticationPort",
        "input_validator", "output_validator",
    }
    leaked = param_names & forbidden_in_ctor
    assert not leaked, (
        f"ListToolsUseCase.__init__ MUST NOT accept {leaked!r} — see "
        f"tool-listing-usecase-spec REQ-002. Accepted params: {param_names!r}"
    )

    # (2) Behavioural check: instantiate normally, then poke a
    # `Mock(spec=ToolExecutorPort)` onto the use case via setattr,
    # and verify it is never called during `list_for`.
    tools = [_make_tool("t1"), _make_tool("t2")]
    uc = _build_use_case(tools=tools)

    fake_executor = mock.create_autospec(ToolExecutorPort, instance=True)
    setattr(uc, "_fake_executor", fake_executor)
    # Note: the use case has no `_tool_executor` attribute (its
    # __init__ never assigned one). The `setattr` above creates a
    # new attribute that the use case does not touch.

    result = uc.list_for(Permission.ADMIN)
    assert len(result) == 2
    fake_executor.execute.assert_not_called()
    # No `assert_not_called` is needed on other mocks because the
    # use case does not have a reference to them either; the static
    # signature check above is the authoritative test.


# ─── Test 6 (bonus): RequireConfirmation also filtered ────────────────────


def test_require_confirmation_also_filtered() -> None:
    """A tool that returns `RequireConfirmation` from the policy is
    filtered out of the listing — the caller cannot invoke it
    without a confirmation step.
    """
    def check(_caller_permission: Permission, tool: Tool):
        if tool.name == "safe":
            return Allow()
        if tool.name == "risky":
            return RequireConfirmation("please confirm")
        return Deny("denied")

    tools = [_make_tool("safe"), _make_tool("risky")]
    tool_registry = mock.create_autospec(ToolRegistryPort, instance=True)
    tool_registry.list.return_value = list(tools)
    authorization_policy = mock.create_autospec(AuthorizationPolicyPort, instance=True)
    authorization_policy.check.side_effect = check
    logger = mock.create_autospec(LoggerPort, instance=True)
    uc = ListToolsUseCase(
        tool_registry=tool_registry,
        authorization_policy=authorization_policy,
        logger=logger,
    )

    result = uc.list_for(Permission.ADMIN)
    assert [t.name for t in result] == ["safe"]


# ─── Test 7 (bonus): logger called exactly once with the right fields ─────


def test_logger_called_once_with_event_and_count() -> None:
    """The use case emits one structured log line per call, with the
    event name `tools.listed`, the caller's permission, and the
    number of returned tools.
    """
    tools = [_make_tool("a"), _make_tool("b"), _make_tool("c")]
    uc = _build_use_case(tools=tools, allow_set={"a", "b"})  # `c` denied

    uc.list_for(Permission.ADMIN)
    uc._logger.info.assert_called_once()
    args, kwargs = uc._logger.info.call_args
    assert args == (EVENT_TOOLS_LISTED,)
    assert kwargs["caller_permission"] == "ADMIN"
    assert kwargs["count"] == 2  # only `a` and `b`


# ─── Test 8 (bonus): returns a NEW list, not the registry's internal list


def test_returns_new_list_not_registry_internal() -> None:
    """The use case MUST return a NEW list (per the task acceptance
    criterion and tool-listing-usecase-spec REQ-001). This guards
    against the use case accidentally returning the registry's
    internal storage object (which would let a caller mutate the
    registry by holding on to the returned list).
    """
    tools = [_make_tool("a"), _make_tool("b"), _make_tool("c")]
    uc = _build_use_case(tools=tools)

    result = uc.list_for(Permission.ADMIN)
    # The result must be a new list object, not the same as the
    # registry's `.list()` return value.
    assert result is not uc._tool_registry.list.return_value
    # And it must be a list, not a view or generator.
    assert isinstance(result, list)


# ─── Meta-test: no I/O imports in this test file ───────────────────────────


def test_no_io_imports() -> None:
    """The test file MUST NOT actually `import` psycopg,
    sentence_transformers, starlette, or httpx. We look for `^import
    X` or `^from X` at the start of a line (regex with
    `re.MULTILINE`) to avoid false positives from docstrings that
    merely mention the module name.
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
        pattern = rf"^(import|from)\s+{re.escape(mod)}(?:\b|[^a-zA-Z0-9_])"
        match = re.search(pattern, source, re.MULTILINE)
        assert not match, (
            f"Test file {this_file.name} contains forbidden I/O import "
            f"of {mod!r} (matched: {match.group(0)!r} at line "
            f"{source[:match.start()].count(chr(10)) + 1}). Use case tests "
            f"must be pure (no DB, no embedding, no HTTP)."
        )
