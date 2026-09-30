FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml /app/
COPY src /app/src
RUN pip install -U pip && pip install -e .
CMD ["python", "-m", "dayz_discord_ops.bot"]
