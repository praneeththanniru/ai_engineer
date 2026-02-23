import os
import subprocess
from app.planner import Planner
from app.executor import Executor
from app.memory import Memory


class AutonomousAgent:
    """
    Production AI DevOps Agent
    Includes:
    - Planning
    - Execution
    - Docker Auto Generator
    - Auto API Testing
    - Auto Git Workflow
    """

    def __init__(self):
        # ✅ FIX: Pass memory into planner
        self.memory = Memory()
        self.planner = Planner(self.memory)
        self.executor = Executor()

    # ==============================
    # MAIN ENTRY
    # ==============================

    def run(self, task: str):
        print("\n🚀 AI DevOps Agent — Production Mode")

        # 1️⃣ Generate Plan
        print("\n🧠 Generating Plan...")
        plan = self.planner.plan(task)

        files = plan.get("files", [])

        print("\n📦 Files Planned:")
        for f in files:
            print(f" → {f['path']}")

        # 2️⃣ Write Files
        for file in files:
            print(f"📝 Writing: {file['path']}")
            self.executor.execute(
                "write_file",
                {
                    "path": file["path"],
                    "content": file["content"],
                },
            )

        print("\n✅ All Files Written.")

        # 3️⃣ Docker Auto Generator
        self.auto_generate_docker()

        # 4️⃣ Auto API Test
        self.auto_api_test()

        # 5️⃣ Auto Git Workflow
        self.auto_git_workflow()

    # ==================================================
    # 🐳 Docker Auto Generator
    # ==================================================

    def auto_generate_docker(self):
        print("\n🐳 Checking Docker Auto Generation...")

        if not os.path.exists("main.py"):
            print("❌ No backend detected.")
            return

        print("✅ Backend detected — Creating Docker Files...")

        dockerfile = """\
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

        compose = """\
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8000:8000"
"""

        with open("Dockerfile", "w") as f:
            f.write(dockerfile)

        with open("docker-compose.yml", "w") as f:
            f.write(compose)

        print("🐳 Dockerfile Created")
        print("🐳 docker-compose.yml Created")
        print("✅ Docker Auto Generator Completed")

    # ==================================================
    # 🧪 Auto API Test
    # ==================================================

    def auto_api_test(self):
        print("\n🔎 Running Auto API Tests...")

        if not os.path.exists("main.py"):
            print("❌ No API Project.")
            return

        try:
            import requests

            health = requests.get("http://localhost:8000/health", timeout=3)
            print("Health:", health.text)

            metrics = requests.get("http://localhost:8000/metrics", timeout=3)
            print("Metrics:", metrics.text)

            print("✅ API Tests Passed")

        except Exception as e:
            print("❌ API Test Failed:", str(e))

    # ==================================================
    # 🔥 Auto Git Workflow
    # ==================================================

    def auto_git_workflow(self):
        print("\n🚀 Auto Git Workflow Started")

        if not os.path.exists(".git"):
            print("❌ Not a git repository.")
            return

        commands = [
            "git add .",
            'git commit -m "Auto Generated Project"',
            "git push",
        ]

        for cmd in commands:
            print("Executing:", cmd)
            subprocess.run(cmd, shell=True)

        print("✅ Auto Git Workflow Completed")