import os

# --------------------------------------------------
# App
# --------------------------------------------------
APP_NAME = "Ingest & RAG API"
API_PREFIX = "/v1"

ENV = os.getenv("ENV", "local")  # local | production

# --------------------------------------------------
# Feature Flags
# --------------------------------------------------
USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

# --------------------------------------------------
# OpenAI
# --------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

# --------------------------------------------------
# Pinecone
# --------------------------------------------------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")

if not PINECONE_API_KEY or not PINECONE_HOST:
    raise RuntimeError("PINECONE_API_KEY and PINECONE_HOST are required")

# --------------------------------------------------
# Firestore
# --------------------------------------------------
FIRESTORE_PROJECT = os.getenv("FIRESTORE_PROJECT")
if not FIRESTORE_PROJECT:
    raise RuntimeError("FIRESTORE_PROJECT is required")

# --------------------------------------------------
# Redis / Celery (Production only)
# --------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")

if USE_CELERY and not REDIS_URL:
    raise RuntimeError("REDIS_URL is required when USE_CELERY=true")
