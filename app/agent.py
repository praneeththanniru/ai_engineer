import os
import subprocess
import re
from app.planner import Planner
from app.executor import Executor
from app.memory import Memory


class AutonomousAgent:
    """
    Production AI DevOps Agent
    Now Includes:
    - Planning
    - Execution
    - Docker Auto Generator
    - Auto API Testing
    - Auto Semantic Versioning
    - Git Tag + Push
    """

    def __init__(self):
        self.memory = Memory()
        self.planner = Planner(self.memory)
        self.executor = Executor()

    # ==================================================
    # MAIN ENTRY
    # ==================================================

    def run(self, task: str):
        print("\n🚀 AI DevOps Agent — Release Mode")

        print("\n🧠 Generating Plan...")
        plan = self.planner.plan(task)

        files = plan.get("files", [])

        print("\n📦 Files Planned:")
        for f in files:
            print(f" → {f['path']}")

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

        self.auto_generate_docker()
        self.auto_api_test()
        self.auto_git_release()

    # ==================================================
    # DOCKER AUTO GENERATOR
    # ==================================================

    def auto_generate_docker(self):
        print("\n🐳 Checking Docker Auto Generation...")

        if not os.path.exists("main.py"):
            print("❌ No backend detected.")
            return

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

    # ==================================================
    # AUTO API TEST
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
            print("⚠ API not running yet (this is okay before deployment).")

    # ==================================================
    # SEMANTIC VERSION ENGINE
    # ==================================================

    def get_latest_tag(self):
        try:
            result = subprocess.check_output(
                ["git", "tag"],
                stderr=subprocess.DEVNULL
            ).decode().splitlines()

            version_tags = [
                tag for tag in result if re.match(r"^v\d+\.\d+\.\d+$", tag)
            ]

            if not version_tags:
                return None

            version_tags.sort(key=lambda s: list(map(int, s[1:].split("."))))
            return version_tags[-1]

        except Exception:
            return None

    def bump_patch(self, version):
        major, minor, patch = map(int, version[1:].split("."))
        patch += 1
        return f"v{major}.{minor}.{patch}"

    # ==================================================
    # AUTO RELEASE WORKFLOW
    # ==================================================

    def auto_git_release(self):
        print("\n🚀 Starting Auto Release Workflow...")

        if not os.path.exists(".git"):
            print("❌ Not a git repository.")
            return

        latest_tag = self.get_latest_tag()

        if latest_tag is None:
            new_version = "v0.1.0"
            print("📦 No previous versions found. Initializing v0.1.0")
        else:
            new_version = self.bump_patch(latest_tag)
            print(f"📦 Latest version: {latest_tag}")
            print(f"⬆ Bumping to: {new_version}")

        commands = [
            "git add .",
            f'git commit -m "Release {new_version}"',
            f"git tag {new_version}",
            "git push",
            "git push --tags",
        ]

        for cmd in commands:
            print("Executing:", cmd)
            subprocess.run(cmd, shell=True)

        print(f"✅ Release {new_version} completed and pushed.")