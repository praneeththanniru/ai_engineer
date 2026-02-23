from app.prompts import SYSTEM_PROMPT


class Planner:

    def __init__(self, memory):

        # Inject memory from agent
        self.memory = memory

    # =====================================
    # PLAN FUNCTION
    # =====================================
    def plan(self):

        """
        Generates a structured file plan.
        Uses stored task from memory.
        """

        task = self.memory.get("task", "")

        if not task:
            print("❌ No task found in memory.")
            return None

        print("\n🧠 Generating Plan for Task:")
        print(task)

        # ==============================
        # Simple Smart Rule-Based Planner
        # ==============================

        files = []

        # Always generate main app
        files.append({
            "path": "main.py",
            "content": self.generate_main(task)
        })

        # Always generate requirements
        files.append({
            "path": "requirements.txt",
            "content": "fastapi\nuvicorn\nrequests"
        })

        # Always generate README
        files.append({
            "path": "README.md",
            "content": f"# Auto Generated Project\n\nTask:\n{task}"
        })

        return {"files": files}

    # =====================================
    # GENERATE MAIN FILE
    # =====================================
    def generate_main(self, task: str):

        return '''#!/usr/bin/env python3
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return {
        "requests": 0,
        "uptime": "0s"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''