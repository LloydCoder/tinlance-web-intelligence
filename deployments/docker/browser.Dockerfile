FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright HOME=/tmp TWI_BROWSER_ENABLED=true
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY db ./db
RUN pip install --no-cache-dir '.[browser]' && rm -rf /ms-playwright/* && python -m playwright install chromium && useradd --system --uid 10001 --create-home --home-dir /home/twi twi && chown -R twi:twi /app /ms-playwright /home/twi
USER 10001:10001
ENTRYPOINT ["python", "-m", "apps.browser_worker.main"]
