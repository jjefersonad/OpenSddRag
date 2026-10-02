FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --frozen --no-dev

ENV OPENSDDRAG_PROJECT=default
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["opensddrag-server", "server", "start", "--transport", "sse", "--port", "8000"]
