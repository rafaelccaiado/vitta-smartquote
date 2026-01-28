from fastapi import FastAPI
app = FastAPI()

@app.get("/api/{path:path}")
async def root(path: str):
    return {"status": "V23_ALIVE", "message": "FastAPI is running with minimal deps"}
