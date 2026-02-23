import os


class Planner:
    """
    Production Planner
    Generates file plan from task
    """

    def __init__(self, memory):
        self.memory = memory

    # ==========================================
    # PLAN METHOD
    # ==========================================

    def plan(self, task: str):
        """
        Accept task as input.
        Generate project files dynamically.
        """

        if not task:
            task = "Build default fastapi project"

        print("\n🧠 Task Received:")
        print(task)

        files = []

        # ✅ Detect FastAPI project automatically
        if "/health" in task or "/metrics" in task or "fastapi" in task:
            files.append(
                {
                    "path": "main.py",
                    "content": self.generate_fastapi(),
                }
            )

            files.append(
                {
                    "path": "requirements.txt",
                    "content": "fastapi\nuvicorn\nrequests",
                }
            )

            files.append(
                {
                    "path": "README.md",
                    "content": "# Auto Generated FastAPI Project",
                }
            )

        return {"files": files}

    # ==========================================
    # FASTAPI GENERATOR
    # ==========================================

    def generate_fastapi(self):
        return """\
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
"""