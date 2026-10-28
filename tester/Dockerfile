# ==============================================================================
# Service: tester (Automated Integration Test Runner)
# Base Image: Python 3.11 Alpine (Lightweight client container)
# ==============================================================================
FROM python:3.11-alpine

LABEL maintainer="Katari Venu (12341110)"
LABEL description="Automated End-to-End Integration Tester for Proximity Search API"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    TARGET_URL=http://web:80

WORKDIR /test

COPY integration_test.py /test/integration_test.py

CMD ["python", "integration_test.py"]
