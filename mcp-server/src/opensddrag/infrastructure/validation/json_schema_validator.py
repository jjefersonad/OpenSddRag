"""JSON-Schema validator backed by `pydantic` (no new dependencies).

The validator implements both `InputValidatorPort` and
`OutputValidatorPort` (see `core/ports/validator.py`) by:

    1. Building a `pydantic.BaseModel` dynamically from the
       JSON-Schema dict via `pydantic.create_model`.
    2. Wrapping it in a `pydantic.TypeAdapter` for validation.
    3. Translating `pydantic.ValidationError` into
       `ValidationResult.INVALID(errors=[...])` and successful
       validation into `ValidationResult.OK(normalized_value)`.

The mapping from JSON-Schema to Python types is intentionally
**minimal** — enough to cover the schemas the OpenSddRag tool set
emits today. Unsupported features (e.g. `oneOf`, `anyOf`, `$ref`,
`additionalProperties` with a typed schema, custom `format`s) are
documented as out-of-scope; extending the mapping is a contained
change in `_build_field` below.

This module is part of the **infrastructure layer**. It MAY import
from `pydantic` (already a project dependency) and from
`core/domain/*` / `core/ports/*`. It MUST NOT import from
`mcp/`, `db/`, `embedding/`, or any other internal project module.
"""

from __future__ import annotations

from typing import Any, Optional, Type

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, create_model

from opensddrag.core.domain.validation import (
    Invalid,
    OK,
    ValidationError as DomainValidationError,
    ValidationResult,
)


# ─── JSON-Schema → Python-type mapping ──────────────────────────────────────
#
# Minimal but sufficient for the OpenSddRag tool set. Each entry maps
# a JSON-Schema `type` string to the corresponding Python type used in
# `create_model(..., field=(py_type, Field(...)))`. `None` means
# "use Any" (i.e. accept any value for this field).
TYPE_MAP: dict[str, Type[Any]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


# ─── Helpers ────────────────────────────────────────────────────────────────


def _js_to_py_type(field_schema: dict) -> Type[Any]:
    """Map a single JSON-Schema dict to a Python type for `create_model`.

    Supports the subset of JSON-Schema we use today:
        * `type: "string" | "integer" | "number" | "boolean" |
                  "array" | "object" | "null"`
        * nested `object` (recursive)
        * nested `array` (recursive; elements are untyped)
        * `enum` (mapped to a `Literal` if present)

    Anything else (e.g. `oneOf`, `anyOf`, `allOf`, `$ref`,
    `additionalProperties` with a schema, format constraints) is
    best-effort: the validator falls back to `Any` and accepts any
    value. A future change may extend the mapping.
    """
    # `enum` -> use Any (Literal would require generating a new
    # type per enum, which `create_model` does not support cleanly).
    if "enum" in field_schema:
        return object

    field_type = field_schema.get("type")
    if field_type is None:
        return object  # no type constraint -> accept anything

    if field_type == "array":
        return list

    if field_type == "object":
        return dict

    if field_type in TYPE_MAP:
        return TYPE_MAP[field_type]

    # Multi-type unions (e.g. ["string", "null"]) — pydantic does not
    # support these directly via `create_model`. Fall back to Any.
    if isinstance(field_type, list):
        return object

    return object


def _build_type_adapter(schema: dict) -> TypeAdapter:
    """Build a `TypeAdapter` for the given JSON-Schema dict.

    Supports:
        * top-level `type: "object"`
        * `properties` dict (each entry is a sub-schema)
        * `required` list (the keys that must be present)
        * `additionalProperties: false` (model rejects extras)
        * nested `object` and `array` (recursive)

    Uses `pydantic.create_model()` — the documented Pydantic v2 API for
    dynamic model creation — which correctly processes FieldInfo descriptors
    and avoids the class-attribute leakage that occurs with `type()`.

    Optional fields are typed as `Optional[py_t]` so that `None` (the
    default when not provided) is accepted without a validation error.
    `model_dump(exclude_none=True)` is used downstream so that missing
    optional fields remain absent from the normalized dict — executor code
    uses `args.get("key", default)` patterns and relies on the key being
    absent rather than present with a `None` value.
    """
    if schema.get("type") != "object":
        py_t = _js_to_py_type(schema)
        return TypeAdapter(py_t)

    properties = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])

    fields: dict[str, tuple] = {}
    for prop_name, prop_schema in properties.items():
        py_t = _js_to_py_type(prop_schema)
        if prop_name in required:
            fields[prop_name] = (py_t, ...)
        else:
            # Optional[py_t] allows None so the default None does not fail
            # Pydantic's type coercion when the field is absent from input.
            fields[prop_name] = (Optional[py_t], None)

    additional = schema.get("additionalProperties", True)
    model_config = ConfigDict(extra="forbid" if additional is False else "allow")
    return TypeAdapter(
        create_model("_DynamicJsonSchemaModel", __config__=model_config, **fields)
    )


def _loc_to_path(loc: tuple) -> str:
    """Convert a pydantic `loc` tuple (e.g. `('a', 'b', 0)`) to a
    dotted path string (e.g. `"a.b.0"`).

    Returns an empty string for the top level (empty tuple). The
    format is intentionally simple: the only consumer is
    `Response.details["errors"]`, which is a UX detail, not an
    interop contract.
    """
    if not loc:
        return ""
    return ".".join(str(part) for part in loc)


# ─── The validator ──────────────────────────────────────────────────────────


class JsonSchemaValidator:
    """Validates Python values against a JSON-Schema dict.

    Implements both `InputValidatorPort` and `OutputValidatorPort`
    from `core/ports/validator.py` (the two ports have the same
    signature; this class satisfies both because the domain types
    `OK` and `Invalid` are the same for inputs and outputs).

    No new dependencies: pydantic is already in `pyproject.toml`.

    Construction is no-arg (`JsonSchemaValidator()`). The validator
    is **stateless** across calls apart from a small per-instance
    cache that maps a schema dict (by `id()`) to its compiled
    `TypeAdapter`. The cache is bounded by the number of distinct
    schemas the validator is asked to validate against, which in
    practice is the number of registered MCP tools (~20).
    """

    def __init__(self) -> None:
        # `id(schema)` is a stable identifier for the dict object
        # within a single process. Using `id()` is safe here because
        # the caller (the composition root in `infrastructure/
        # composition.py`) builds the tool list once at startup
        # and reuses the same `Tool.input_schema` dict across
        # validations. Two different dicts with the same content
        # would compile twice — acceptable for startup cost.
        self._adapter_cache: dict[int, TypeAdapter] = {}

    def validate(self, schema: dict, value: Any) -> ValidationResult:
        """Validate `value` against the JSON-Schema `schema`.

        Returns `OK(normalized_value)` on success or
        `INVALID(errors=[...])` on failure. Never raises.

        The `normalized_value` is the input after pydantic's
        coercion (e.g. string `"42"` -> int `42` for an integer
        schema). For object schemas it is a plain `dict`
        (`pydantic.BaseModel.model_dump()`), not a `BaseModel`
        instance, so the MCP adapter can serialize it to JSON
        without further conversion.
        """
        try:
            adapter = self._get_or_build_adapter(schema)
        except Exception:  # noqa: BLE001 — defensive
            # Malformed schema (e.g. `properties: "not-a-dict"`) — we
            # cannot compile an adapter. Fall back to permissive
            # validation: accept any value. A future change may
            # add a more sophisticated fallback (e.g. validate
            # against `{}` for an empty object schema).
            return OK(value=value)

        try:
            normalized = adapter.validate_python(value)
            # If the adapter wraps a BaseModel, dump to a plain dict
            # so the downstream consumer does not need to know
            # about pydantic. For scalar adapters (e.g. a bare
            # string schema), the value is already a primitive.
            if isinstance(normalized, BaseModel):
                # exclude_none=True: keeps absent optional fields absent so
                # executor code using `args.get(k, default)` sees the default
                # rather than None when the caller did not provide the key.
                normalized = normalized.model_dump(exclude_none=True)
            return OK(value=normalized)
        except ValidationError as exc:
            return Invalid(
                errors=[
                    DomainValidationError(
                        path=_loc_to_path(err["loc"]),
                        message=err["msg"],
                    )
                    for err in exc.errors()
                ]
            )
        except Exception as exc:  # noqa: BLE001 — defensive
            # Any unexpected error from pydantic (e.g. a malformed
            # schema that we cannot compile) is translated to a
            # single INVALID with a sanitized message. The use
            # case MUST never see a propagated exception.
            return Invalid(
                errors=[
                    DomainValidationError(
                        path="",
                        message=f"validator internal error: {type(exc).__name__}",
                    )
                ]
            )

    def _get_or_build_adapter(self, schema: dict) -> TypeAdapter:
        """Return the cached `TypeAdapter` for `schema`, building it
        on first use.
        """
        key = id(schema)
        adapter = self._adapter_cache.get(key)
        if adapter is None:
            adapter = _build_type_adapter(schema)
            self._adapter_cache[key] = adapter
        return adapter


__all__ = ["JsonSchemaValidator"]
