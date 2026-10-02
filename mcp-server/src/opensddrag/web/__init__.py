"""OpenSddRag web — REST delivery adapter for the /api/v1 management API.

This package is the REST delivery layer described by the
`web-management-system` mcp-server delta (REQ-011/REQ-012): Starlette
routes under `/api/v1`, mounted only in HTTP/SSE mode. Handlers delegate
to the shared persistence layer wired in the composition root — this
package MUST NOT import `opensddrag.db` directly (enforced by
`tests/architecture/test_imports.py::test_web_adapter_does_not_import_repositories`).
"""