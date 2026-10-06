FROM python:3.12-slim-bookworm

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY services/gsc_mcp/requirements.txt /app/requirements-gsc-mcp.txt
RUN pip install --no-cache-dir -r /app/requirements-gsc-mcp.txt

COPY services/gsc_mcp /app/services/gsc_mcp

ENV PYTHONPATH=/app
# MCP_HOST / MCP_PORT set at runtime (production: MCP_HOST=0.0.0.0, loopback publish on host).
ENV MCP_PORT=8010

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health')" || exit 1

CMD ["python", "-m", "services.gsc_mcp"]
