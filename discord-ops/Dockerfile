FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Copy dependency definitions first
COPY pyproject.toml /app/

# Install system dependencies
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN git config --global --add safe.directory /app

# Install python dependencies (CACHED layer)
COPY requirements.txt /app/
RUN pip install -U pip && pip install -r requirements.txt

# Now copy the rest of the code
COPY . /app

# Re-install to install the project itself (fast)
RUN pip install .

CMD ["python", "-m", "src.mildlyawesome.main"]
