"""No-op authenticator — the default `AuthenticationPort` for development.

This is the implementation that ships with the server **out of the
box** (see `infrastructure/composition.py`). It accepts every caller
and grants the highest permission level (`Permission.ADMIN`), so the
use case works in development without an authentication subsystem in
place. Production deployments MUST swap this for a real
implementation (e.g. an API-key lookup or a future OAuth/JWT
verifier) via the composition root.

`resolve(caller_id)` preserves the `caller_id` for logging purposes
(so every log line still tags the call with the right identity)
but **always** returns `Permission.ADMIN`. This is a deliberate
trust-grant: the assumption is that the transport layer (e.g. the
HTTP `AuthMiddleware` in `mcp/auth.py`, or stdio being a local
process) has already validated the caller's identity and that we
are inside a trusted boundary.

A future change may introduce a `JwtAuthenticator` that derives
the permission from a JWT claim — see
`mcp-infrastructure-spec` REQ-003 Scenario "Future JWT
implementation is a drop-in". That implementation will be a
drop-in replacement for this one.

This module is part of the **infrastructure layer** (auth/
sub-package). It imports only from `core.domain.*` and
`core.ports.*` (the dependency-inversion seam) — it MUST NOT
import from `mcp/`, `db/`, `embedding/`, or `config/`.
"""

from __future__ import annotations

from opensddrag.core.domain.permission import Permission
from opensddrag.core.ports.authentication import AuthenticationPort, Caller


class NoopAuthenticator:
    """Default `AuthenticationPort` that grants `Permission.ADMIN` to
    every caller.

    Construction is no-arg: `NoopAuthenticator()`. The class holds
    no state, so the same instance can be shared across all
    invocations in a single process.

    Why "no-op" is a safe default:
        * **stdio transport**: the local process is trusted by
          construction (the OS already authenticated the user
          running the server).
        * **HTTP transport**: the HTTP `AuthMiddleware` in
          `mcp/auth.py` validates the API key BEFORE the request
          reaches the MCP adapter. By the time `resolve` is called,
          we are inside a boundary that is already trusted — the
          no-op authenticator says "the call has already passed
          upstream checks, so grant the highest permission".
    """

    def __init__(self) -> None:
        # No state to hold. The class is intentionally stateless
        # so a single instance can be shared across the server
        # lifetime.
        pass

    def resolve(self, caller_id: str) -> Caller:
        """Return a `Caller` with the given `caller_id` and `ADMIN`
        permission.

        The `caller_id` is preserved unchanged (it is the stable
        identifier the rate limiter and logger use to bucket the
        caller's activity). The `permission` is **always**
        `Permission.ADMIN`, regardless of the input — this is the
        whole point of the no-op implementation.

        Implementations of the future `JwtAuthenticator` may
        look up the caller's permission from a JWT claim here
        and return a different `Permission` value. The use case
        is unaffected by that change because it consumes the
        `Caller` returned by this method, not the input
        `caller_id`.
        """
        return Caller(caller_id=caller_id, permission=Permission.ADMIN)


__all__ = ["NoopAuthenticator"]
