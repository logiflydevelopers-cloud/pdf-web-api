from fastapi import FastAPI
from app.config import APP_NAME, API_PREFIX
from app.routes import router

app = FastAPI(
    title=APP_NAME,
    version="1.0.0"
)

# ---------------------------
# Routes
# ---------------------------
app.include_router(router)

# ---------------------------
# Health check (Render needs this)
# ---------------------------
@app.get("/", tags=["health"])
def health():
    return {
        "status": "ok",
        "service": APP_NAME
    }

