FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 HOME=/tmp
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends ca-certificates python3.12 python3.12-venv && rm -rf /var/lib/apt/lists/*
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY db ./db
RUN pip install --no-cache-dir '.[integration]' && pip check && useradd --system --uid 10001 --create-home --home-dir /home/twi twi && chown -R twi:twi /app /home/twi
USER 10001:10001
CMD ["python", "-m", "apps.worker.main"]
