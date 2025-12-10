FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY requirements.txt /app/project_requirements.txt
RUN pip install --no-cache-dir -r /app/project_requirements.txt

COPY .streamlit .

COPY dashboard.py .
COPY entrypoint.sh .

COPY .env .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
