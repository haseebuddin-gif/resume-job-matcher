# Production image (used for Hugging Face Spaces; works on any Docker host).
#   docker build -t skillmatch .  &&  docker run -p 7860:7860 skillmatch

# ---- 1. build the Angular frontend
FROM node:24-slim AS web
ENV NG_CLI_ANALYTICS=false
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx ng build

# ---- 2. Python API + NLP models
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/app/.hf
WORKDIR /app

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt && python -m spacy download en_core_web_sm
# bake the default model into the image so the first request is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .
COPY --from=web /web/dist ./frontend/dist

# Spaces run the container as uid 1000
RUN useradd -m -u 1000 user && chown -R user /app
USER user

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
