"""ExecuteToolUseCase — the central use case of the OpenSddRag MCP server.

This is the **orchestration layer** of the architecture: it implements the
full tool-invocation pipeline (lookup → authentication resolve → rate
limit → input validation → authorization → execution → output validation
→ response) by delegating every step to a **port** (interface) that is
injected at construction time.

Key contract (from `tool-execution-usecase-spec` REQ-001): the use case
is a **total function** — it returns a `Response` for every code path and
never raises. The MCP adapter and any future REST/CLI adapter can rely
on this to map the response to its wire format without try/except.

Pipeline order is **fixed** (REQ-003) and is enforced both by code and
by `tests/core/test_execute_tool_usecase.py::test_order_enforcement`,
which records the sequence of port calls.

This module is part of the **use-case layer** (core/usecases/). It MUST
NOT import from any internal project module other than `core.domain`
and `core.ports`. The architecture test in
`tests/architecture/test_imports.py::test_usecases_have_no_infra_or_db_imports`
enforces this.
"""

from __future__ import annotations

import time
from typing import Any

from opensddrag.core.domain.permission import Allow
from opensddrag.core.domain.request import Request
from opensddrag.core.domain.response import Response
from opensddrag.core.domain.validation import Invalid
from opensddrag.core.ports.authentication import AuthenticationPort, Caller
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.core.ports.validator import InputValidatorPort, OutputValidatorPort


# Canonical event name for the success log line. Used by both the use
# case and the test that records port-call order. Keeping it as a
# module-level constant makes a typo in the test a NameError rather
# than a silent mismatch.
EVENT_TOOL_EXECUTED = "tool.executed"


class ExecuteToolUseCase:
    """Orchestrates the full tool-invocation pipeline.

    Every port is **required** (no defaults). The composition root in
    `infrastructure/composition.py` is the only place that wires
    concrete adapters to these ports (see `task-composition-1`).
    """

    def __init__(
        self,
        *,
        tool_registry: ToolRegistryPort,
        authenticator: AuthenticationPort,
        rate_limiter: RateLimiterPort,
        input_validator: InputValidatorPort,
        authorization_policy: AuthorizationPolicyPort,
        tool_executor: ToolExecutorPort,
        output_validator: OutputValidatorPort,
        logger: LoggerPort,
    ) -> None:
        # Keyword-only so the call site is self-documenting and the
        # order of arguments does not matter (a future addition of a
        # 9th port won't break every call site in tests).
        self._tool_registry = tool_registry
        self._authenticator = authenticator
        self._rate_limiter = rate_limiter
        self._input_validator = input_validator
        self._authorization_policy = authorization_policy
        self._tool_executor = tool_executor
        self._output_validator = output_validator
        self._logger = logger

    async def execute(
        self,
        name: str,
        parameters: dict[str, Any],
        caller: Caller,
    ) -> Response:
        """Run the full pipeline and return a `Response`.

        The signature accepts `Caller` (not just `Permission`) per the
        design decision "`ExecuteToolUseCase` carries a `Caller` object,
        not just `Permission`" — `Caller.caller_id` is needed for the
        rate limiter and the logger, both of which are part of the
        pipeline.

        Returns a `Response` for every code path; never raises for any
        domain-level error (see `tool-execution-usecase-spec` REQ-001
        Scenario "Executor error" for the catch-all rule).
        """
        # ── Step 1: registry lookup ──────────────────────────────────
        # `get` is the only port that may legitimately return `None`;
        # every other port either returns a structured value or raises
        # (which we handle below).
        tool = self._tool_registry.get(name)
        if tool is None:
            return self._log_and_return(
                caller=caller,
                tool_name=name,
                result_status="error",
                response=Response.error(
                    "TOOL_NOT_FOUND",
                    f"no tool registered with name {name!r}",
                ),
                duration_ms=0,
            )

        # ── Step 2: authentication resolve ──────────────────────────
        # The Caller was already built by the adapter. `authenticator`
        # is the use-case-level port that translates the opaque
        # `caller_id` into a `Caller` with a `permission`. In the
        # current architecture the Caller passed in already carries the
        # permission the adapter resolved, so we treat the auth port
        # as a *re-resolution* point: a future OAuth/JWT implementation
        # may re-derive the permission from the caller_id (e.g. a JWT
        # claim). For the no-op default, the result is the same
        # `Caller` we received.
        resolved_caller = self._authenticator.resolve(caller.caller_id)
        # If the auth port refused to resolve (returns a synthetic
        # READ_ONLY), keep the caller's id but use the resolved
        # permission. The Caller's `caller_id` is the source of truth
        # for identity; only `permission` may be downgraded.
        effective_caller = Caller(
            caller_id=caller.caller_id,
            permission=resolved_caller.permission,
        )

        # ── Step 3: rate limit ───────────────────────────────────────
        # `allow` returns `(allowed, retry_after)`. When `allowed` is
        # True, `retry_after` is 0 (we ignore it).
        allowed, retry_after = await self._rate_limiter.allow(effective_caller.caller_id)
        if not allowed:
            return self._log_and_return(
                caller=effective_caller,
                tool_name=name,
                result_status="error",
                response=Response.error(
                    "RATE_LIMITED",
                    (
                        f"rate limit exceeded for caller {effective_caller.caller_id!r}; "
                        f"retry after {retry_after} seconds"
                    ),
                    details={"retry_after": retry_after},
                ),
                duration_ms=0,
            )

        # ── Step 4: input validation ─────────────────────────────────
        input_result = self._input_validator.validate(tool.input_schema, parameters)
        if isinstance(input_result, Invalid):
            return self._log_and_return(
                caller=effective_caller,
                tool_name=name,
                result_status="error",
                response=Response.error(
                    "INVALID_INPUT",
                    f"input for tool {name!r} failed validation",
                    details={"errors": [
                        {"path": e.path, "message": e.message}
                        for e in input_result.errors
                    ]},
                ),
                duration_ms=0,
            )
        # input_result is OK; the normalized value MAY differ from
        # `parameters` (e.g. pydantic coerces "42" -> 42 for an int
        # schema). Use the normalized value downstream.
        normalized_parameters = input_result.value

        # ── Step 5: authorization check ──────────────────────────────
        decision = self._authorization_policy.check(
            effective_caller.permission, tool,
        )
        if not isinstance(decision, Allow):
            # Deny(reason) and RequireConfirmation(prompt) both end here.
            # The reason/prompt field of the decision is the
            # human-readable message the adapter will surface to the
            # caller.
            reason = getattr(decision, "reason", None) or getattr(decision, "prompt", None) or "denied"
            code = "FORBIDDEN" if decision.__class__.__name__ == "Deny" else "CONFIRMATION_REQUIRED"
            return self._log_and_return(
                caller=effective_caller,
                tool_name=name,
                result_status="error",
                response=Response.error(code, reason),
                duration_ms=0,
            )

        # ── Step 6: execution (the only step that may take time) ───
        # Measure wall time around the executor call so the log line
        # carries a meaningful `duration_ms`. We use `time.perf_counter`
        # (monotonic, high-resolution) rather than `time.time` (wall
        # clock, can jump backwards on NTP correction).
        t0 = time.perf_counter()
        try:
            executor_result = await self._tool_executor.execute(tool, normalized_parameters)
        except Exception as exc:  # noqa: BLE001 — spec REQ-001 catch-all
            duration_ms = int((time.perf_counter() - t0) * 1000)
            # Log the exception with `last_resort=True` per the spec
            # ("the original exception SHALL be re-raised only as a
            # `last_resort` log detail, never propagated"). We do not
            # re-raise — the catch-all is the contract.
            self._logger.error(
                EVENT_TOOL_EXECUTED,
                tool_name=name,
                caller_id=effective_caller.caller_id,
                duration_ms=duration_ms,
                result_status="error",
                error_code="INTERNAL",
                last_resort=f"{type(exc).__name__}: {exc}",
            )
            return Response.error(
                "INTERNAL",
                f"tool {name!r} raised an exception during execution",
            )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # ── Step 7: output validation ────────────────────────────────
        output_result = self._output_validator.validate(tool.output_schema, executor_result)
        if isinstance(output_result, Invalid):
            return self._log_and_return(
                caller=effective_caller,
                tool_name=name,
                result_status="error",
                response=Response.error(
                    "INVALID_OUTPUT",
                    f"output of tool {name!r} failed validation",
                    details={"errors": [
                        {"path": e.path, "message": e.message}
                        for e in output_result.errors
                    ]},
                ),
                duration_ms=duration_ms,
            )

        # ── Step 8: response ────────────────────────────────────────
        # Happy path. The use case returns a `Response.ok(value)` and
        # then logs the success line via the helper. The helper is
        # called *after* the response is built so a logger failure can
        # never affect the response.
        return self._log_and_return(
            caller=effective_caller,
            tool_name=name,
            result_status="ok",
            response=Response.ok(output_result.value),
            duration_ms=duration_ms,
        )

    def _log_and_return(
        self,
        *,
        caller: Caller,
        tool_name: str,
        result_status: str,
        response: Response,
        duration_ms: int,
    ) -> Response:
        """Emit the structured log line for one invocation and return the response.

        Centralising the logger call here means:
            * The logger is called exactly once per `execute()` call
              (enforced by the test `test_logger_called_exactly_once`).
            * The log fields are uniform across all branches (no
              branch can accidentally drop `caller_id` or
              `result_status`).
            * A future change to the log schema (e.g. adding a
              `project_slug` field) only needs to touch this one
              function.
        """
        # Build the structured fields dict. We use a small helper to
        # make it obvious which fields are emitted.
        log_fields = {
            "tool_name": tool_name,
            "caller_id": caller.caller_id,
            "duration_ms": duration_ms,
            "result_status": result_status,
        }
        # Include the error code on the failure path. `response.code`
        # is only meaningful when `is_ok` is False; we still set it
        # to None on the success path to keep the log schema uniform.
        log_fields["error_code"] = response.code
        self._logger.info(EVENT_TOOL_EXECUTED, **log_fields)
        return response


# Re-export `Request` so the spec's signature comment ("the use case
# accepts a Request or its constituent fields") stays meaningful
# from the import side. `ExecuteToolUseCase` does not take a `Request`
# directly (the design decision was to take `(name, parameters, caller)`
# for symmetry with `ListToolsUseCase.list_for(caller_permission)`),
# but downstream code that wants to materialize a `Request` from
# an HTTP body can import it from the same module.
__all__ = [
    "EVENT_TOOL_EXECUTED",
    "ExecuteToolUseCase",
    "Request",
]
