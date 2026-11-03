# Contentor Linux do QA Lab: aplicação + ferramentas de linha de comandos + terminal no browser
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates bash-completion procps iproute2 curl less nano vim-tiny \
        postgresql-client git jq tree \
    && rm -rf /var/lib/apt/lists/*

# Terminal web (ttyd): binário oficial do projeto, porque não existe pacote no Debian 12
ARG TTYD_VERSION=1.7.7
RUN ARCH="$(uname -m)" \
    && curl -fsSL -o /usr/local/bin/ttyd \
       "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${ARCH}" \
    && chmod +x /usr/local/bin/ttyd \
    && ttyd --version

# Utilizador sem privilégios de root, como num servidor real
RUN useradd --create-home --shell /bin/bash qa \
    && mkdir -p /var/log/qa-lab /opt/qa-lab \
    && chown -R qa:qa /var/log/qa-lab /opt/qa-lab

WORKDIR /opt/qa-lab

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=qa:qa . .

ENV QA_LAB_LOG_DIR=/var/log/qa-lab \
    PYTHONUNBUFFERED=1 \
    PORT=8000

USER qa
EXPOSE 8000 7681

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["bash", "/opt/qa-lab/docker/entrypoint.sh"]
