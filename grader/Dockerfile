# Sandbox image used per submission. Contains the harness, the scientific libraries the labs use and the in-process
# practice-API simulator (labmock). No app code, secrets or tests. Built for the host's architecture (x86-64 or ARM64).
FROM python:3.12-slim
RUN pip install --no-cache-dir "numpy>=2,<3" "pandas>=2.2,<3" "matplotlib>=3.9,<4" "scikit-learn>=1.5,<2" "pillow>=10,<12" "requests>=2.32,<3" \
    && find /usr/local/lib/python3.12/site-packages -name "tests" -type d -prune -exec rm -rf {} + \
    && mkdir /app
COPY sandbox/harness.py /app/harness.py
COPY sandbox/labmock.py /usr/local/lib/python3.12/site-packages/labmock.py
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl HOME=/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
USER 65534:65534
WORKDIR /tmp
