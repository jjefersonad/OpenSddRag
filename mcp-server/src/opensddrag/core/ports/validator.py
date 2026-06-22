"""Input and output validator ports.

Two structurally identical `Protocol`s — one for inputs, one for outputs
— that the use case calls in sequence:

    1. `InputValidatorPort.validate(tool.input_schema, parameters)`
       runs first; on `INVALID`, the use case returns
       `Response.error(code="INVALID_INPUT", details=errors)`.
    2. The executor runs.
    3. `OutputValidatorPort.validate(tool.output_schema, executor_result)`
       runs last; on `INVALID`, the use case returns
       `Response.error(code="INVALID_OUTPUT", details=errors)`.

The two ports are kept separate (not collapsed into one
`ValidatorPort`) so a future implementation can use a different
mechanism for inputs (e.g. pydantic with strict coercion) and outputs
(e.g. a structural-only check that ignores unknown fields).

The reference implementation is `JsonSchemaValidator`
(in `infrastructure/validation/json_schema_validator.py`) which uses
`pydantic.TypeAdapter` to validate the value against a JSON-Schema
dict. The domain types (`OK`, `Invalid`, `ValidationError`,
`ValidationResult`) live in `core/domain/validation.py`.

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module other than
`core.domain`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from opensddrag.core.domain.validation import ValidationResult


@runtime_checkable
class InputValidatorPort(Protocol):
    """Validates the `parameters` dict against a tool's `input_schema`."""

    def validate(self, schema: dict, value: Any) -> ValidationResult:
        """Validate `value` against the JSON-Schema `schema`.

        Args:
            schema: A JSON-Schema-compatible dict — typically
                `tool.input_schema`. MUST be a dict (not a string, not
                `None`); the implementation may assume that.
            value: The value to validate. For input validation this is
                the `parameters` dict the caller submitted; the
                implementation MUST accept any value (including
                non-dict) and return `INVALID` with a meaningful error
                rather than raising.

        Returns:
            * `OK(normalized_value)` — validation passed. The
              `normalized_value` is the input after any coercion the
              implementation applied (e.g. pydantic's
              `TypeAdapter.validate_python` will coerce `"42"` to `42`
              for an `int` schema).
            * `Invalid(errors=[...])` — validation failed. The
              `errors` list is non-empty and each entry is a
              `ValidationError(path=..., message=...)`.

        Implementations MUST NOT raise. `pydantic.ValidationError`
        and `jsonschema.ValidationError` MUST be caught and translated
        to `Invalid(errors=...)` before returning.
        """
        ...


@runtime_checkable
class OutputValidatorPort(Protocol):
    """Validates an executor's return value against a tool's `output_schema`.

    Same contract as `InputValidatorPort` — see above for the full
    semantics. Kept as a separate Protocol so future implementations
    can use different strategies for inputs vs. outputs.
    """

    def validate(self, schema: dict, value: Any) -> ValidationResult:
        """Validate `value` against the JSON-Schema `schema`.

        Returns `OK` or `Invalid`; never raises. See `InputValidatorPort`
        for the full contract.
        """
        ...


__all__ = ["InputValidatorPort", "OutputValidatorPort"]
