import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from opensddrag.config import settings
from opensddrag.db import api_key_repository


def _json_response(status_code: int, error: str) -> Response:
    return Response(
        content=json.dumps({"error": error}),
        status_code=status_code,
        media_type="application/json",
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _json_response(401, "missing authorization header")

        token = auth_header[len("Bearer "):]
        key = await api_key_repository.lookup_by_hash(token)

        if key is None:
            return _json_response(401, "invalid or revoked api key")

        if key.revoked_at is not None:
            return _json_response(401, "invalid or revoked api key")

        from datetime import datetime, timezone
        if key.expires_at is not None and key.expires_at < datetime.now(tz=timezone.utc):
            return _json_response(401, "api key expired")

        # Resolve project slug
        if key.project_id is not None:
            # Project-scoped key: enforce project match
            from opensddrag.db import project_repository
            project = await project_repository.get_project_by_id(key.project_id)
            project_slug = project.slug if project else None

            requested = request.headers.get("X-Project")
            if requested and requested != project_slug:
                return _json_response(403, "api key not authorized for this project")

            request.state.project_slug = project_slug
        else:
            # Global key: use X-Project header or fall back to default
            project_slug = request.headers.get("X-Project") or settings.opensddrag_project
            request.state.project_slug = project_slug

        return await call_next(request)
