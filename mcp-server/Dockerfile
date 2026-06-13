FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system --no-cache -e .

ENV OPENSDDRAG_PROJECT=default

EXPOSE 8000

CMD ["opensddrag-server", "server", "start", "--transport", "sse", "--port", "8000"]
