# Netra AI: one container that runs the Streamlit app.
# Built for Hugging Face Spaces (free CPU, port 7860), but runs anywhere Docker does:
#   docker build -t netra . && docker run -p 7860:7860 --env-file .env netra
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/user \
    FASTEMBED_CACHE_PATH=/home/user/app/.cache/fastembed

# Hugging Face runs containers as user 1000
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=user . .
USER user

# Download the PDF embedding model (~90 MB) into the image now, so no visitor waits for it later
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/home/user/app/.cache/fastembed')"

EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
