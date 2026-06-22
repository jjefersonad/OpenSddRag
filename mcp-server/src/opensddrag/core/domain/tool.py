"""Domain `Tool` value object.

A `Tool` is the in-memory description of an MCP-exposed operation: its
human-readable name, the JSON-Schema that constrains its input and output,
and the minimum `Permission` a caller must hold to invoke it. Tools are
declared statically in the composition root (task-composition-1) and
returned by `ToolRegistryPort.get / list` (see core/ports/tool_registry.py).

This module is part of the **pure domain layer** (core/domain/). It MUST
NOT import from `mcp`, `fastmcp`, `starlette`, `psycopg`, `pydantic_settings`,
`sentence_transformers`, or any internal project module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opensddrag.core.domain.permission import Permission


@dataclass(frozen=True)
class Tool:
    """A registered MCP tool, as seen by the domain layer.

    Frozen so that the registry cannot accidentally mutate a tool after
    registration (the composition root in task-composition-1 builds the
    list of `Tool`s once at startup). `input_schema` and `output_schema`
    are JSON-Schema-compatible dicts; the `JsonSchemaValidator` (see
    infrastructure/validation/json_schema_validator.py) consumes them.

    Fields:
        name:                The stable tool name as exposed on the MCP wire
                             (e.g. "search_semantic"). Must be unique within
                             a project.
        description:         One-sentence human description; surfaced as the
                             MCP `Tool.description` field. Never parsed.
        required_permission: Minimum `Permission` a caller must hold to
                             invoke the tool. The default policy grants
                             access iff caller.permission >= tool.permission.
        input_schema:        JSON-Schema (draft 2020-12) describing the
                             expected `parameters` dict. `JsonSchemaValidator`
                             rejects requests that fail to validate against it
                             (mcp-infrastructure-spec REQ-002 / tool-execution-
                             usecase-spec REQ-001 Scenario "Validation failure").
        output_schema:       JSON-Schema describing the shape the executor
                             is expected to return. Used to reject
                             misbehaving executors early (REQ-001 Scenario
                             "INVALID_OUTPUT").
        metadata:            Free-form dict attached to the tool — not part
                             of the MCP wire format. Useful for tags,
                             capability slugs, or deprecation flags.
                             Non-frozen via `field(default_factory=dict)` to
                             keep the dataclass hashable while still allowing
                             an empty-dict default without mutable-arg
                             footguns (the empty dict is never shared
                             because of `default_factory`).
    """

    name: str
    description: str
    required_permission: Permission
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # JSON-serializability contract from REQ-001 of mcp-domain-core-spec
        # ("The dataclass is JSON-serializable via `json.dumps(tool, default=str)`").
        # We do not actually call json.dumps here (that would couple the
        # domain to the json stdlib at construction time), but we validate
        # the two schema fields are dicts so a misuse raises immediately
        # rather than at serialization time deep inside the MCP adapter.
        if not isinstance(self.input_schema, dict):
            raise TypeError(
                f"Tool.input_schema must be a dict, got {type(self.input_schema).__name__}"
            )
        if not isinstance(self.output_schema, dict):
            raise TypeError(
                f"Tool.output_schema must be a dict, got {type(self.output_schema).__name__}"
            )


__all__ = ["Tool"]
