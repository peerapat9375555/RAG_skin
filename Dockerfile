# ──────────────────────────────────────────────
#  chatbot-service: Flask + RAG (Supabase + bge-m3 + Gemini)
# ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY RAG.py .
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Environment variables (overridable via docker-compose)
ENV LLM_API_KEY=""
ENV LLM_BASE_URL="https://gen.ai.kku.ac.th/api/v1"
ENV LLM_MODEL="gemini-3.1-pro-preview"
ENV SUPABASE_URL=""
ENV SUPABASE_KEY=""

EXPOSE 5001

CMD ["python", "app.py"]
