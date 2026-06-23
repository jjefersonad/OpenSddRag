"""Domain validation types.

`ValidationResult` is the total return type of `InputValidatorPort.validate`
and `OutputValidatorPort.validate` (see core/ports/validator.py). The
`JsonSchemaValidator` (infrastructure/validation/json_schema_validator.py)
implements this port by wrapping `pydantic.TypeAdapter` and translating
its `ValidationError` into the `INVALID` variant.

This module is part of the **pure domain layer** (core/domain/). It MUST
NOT import from `mcp`, `fastmcp`, `starlette`, `psycopg`, `pydantic_settings`,
`sentence_transformers`, or any internal project module — including
`pydantic` itself. The `pydantic` integration lives in the infrastructure
adapter; the domain only knows the result shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationError:
    """A single validation failure, in a JSON-pointer-ish shape.

    Fields:
        path:    Dotted JSON-pointer path to the offending value
                 (e.g. `"parameters.query"` or `"results.0.score"`).
                 An empty string means the value as a whole is wrong
                 (e.g. wrong top-level type).
        message: Human-readable explanation. Safe to log and to surface
                 to the operator.

    The `path` format is intentionally simple (dotted, not RFC 6901 with
    escaped `~` and `/`): the only consumer is `Response.details`, where
    the format is a UX detail, not an interop contract.
    """

    path: str
    message: str


@dataclass(frozen=True)
class OK:
    """Successful validation. `value` is the (possibly normalized) value."""

    value: Any
    kind: str = "ok"


@dataclass(frozen=True)
class Invalid:
    """Failed validation. `errors` is the (possibly empty) list of errors."""

    errors: list[ValidationError]
    kind: str = "invalid"


# Tagged union. Same pattern as `AuthorizationDecision` in permission.py.
# Implemented as two frozen dataclasses (not a single class with an enum
# field) so consumers can use `isinstance(result, OK)` / `isinstance(result, Invalid)`
# without comparing string discriminators. The `kind` field is present for
# serialization (e.g. when `ValidationResult` ends up inside a `Response.details`).
ValidationResult = OK | Invalid


def is_valid(result: ValidationResult) -> bool:
    """Return True iff `result` is an `OK`."""
    return isinstance(result, OK)


__all__ = [
    "Invalid",
    "OK",
    "ValidationError",
    "ValidationResult",
    "is_valid",
]
