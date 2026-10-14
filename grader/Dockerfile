# Sandbox image used per submission. Contains only the harness; no app code, secrets or tests.
FROM python:3.12-slim
RUN mkdir /app
COPY sandbox/harness.py /app/harness.py
USER 65534:65534
WORKDIR /tmp
