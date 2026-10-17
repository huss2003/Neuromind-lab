# Sandbox image used per submission. Contains the harness, the pinned scientific libraries the labs use and the in-process
# practice-API simulator (labmock). No app code, secrets or tests. Built for the host's architecture (x86-64 or ARM64).
# Reproducible runtime: Python 3.13 + requirements-sandbox.lock (the exact versions the lab packs were verified with).
# Nothing is downloaded while a learner's program runs (the container has no network at all).
FROM python:3.13-slim
COPY requirements-sandbox.lock /tmp/requirements-sandbox.lock
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements-sandbox.lock \
    && pip check \
    && find /usr/local/lib/python3.13/site-packages -name "tests" -type d -prune -exec rm -rf {} + \
    && rm /tmp/requirements-sandbox.lock \
    && mkdir /app
COPY sandbox/harness.py /app/harness.py
COPY sandbox/labmock.py /usr/local/lib/python3.13/site-packages/labmock.py
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl HOME=/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
USER 65534:65534
WORKDIR /tmp
