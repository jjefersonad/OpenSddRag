import asyncio

from opensddrag.config import settings
from opensddrag.db import project_repository


async def resolve_project_id(project_slug: str | None):
    slug = project_slug or settings.opensddrag_project
    project = await project_repository.require_project(slug)
    return project.id, slug
