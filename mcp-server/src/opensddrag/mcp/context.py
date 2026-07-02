from contextvars import ContextVar

_caller_project_var: ContextVar[str | None] = ContextVar("caller_project", default=None)


def set_caller_project(slug: str | None) -> None:
    _caller_project_var.set(slug)


def get_caller_project() -> str | None:
    return _caller_project_var.get()
