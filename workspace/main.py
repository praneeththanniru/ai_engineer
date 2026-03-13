#!/usr/bin/env python3
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return {"requests": 0, "uptime": "0s"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
