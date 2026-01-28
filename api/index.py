from fastapi import FastAPI

app = FastAPI()

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Vercel API is working"}

@app.get("/api/ping")
def ping():
    return "pong"
