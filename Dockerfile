FROM python:3.9-slim

WORKDIR /app

# 1. First copy ONLY the essential files for installation
COPY setup.py requirements.txt README.md ./

# 2. Copy the package directory
COPY task_scheduler/ task_scheduler/

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Install package
RUN pip install --no-cache-dir -e .

# 4. Now copy the remaining files (tests, data, etc.)
COPY tests/ tests/
COPY data/ data/

# Install test dependencies (if any)
RUN pip install pytest

# Run tests
RUN python -m pytest tests/ -v

ENTRYPOINT ["python", "-m", "task_scheduler.main"]
CMD ["--help"]                # Default arguments

# Verify installation
RUN python -c "import task_scheduler; print('Import successful')"


