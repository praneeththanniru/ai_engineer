import subprocess
import requests
from app.planner import Planner
from app.executor import Executor


class AutonomousAgent:

    def __init__(self):

        # simple memory
        self.memory = {}

        # planner now receives memory
        self.planner = Planner(memory=self.memory)

    # =====================================
    # MAIN ENTRY
    # =====================================
    def run(self, task: str):

        print("🚀 AI DevOps Agent — Production Mode")

        # FIX 🔥
        # If your planner doesn't accept task,
        # store task inside memory instead
        self.memory["task"] = task

        plan = self.planner.plan()

        if not plan:
            print("❌ No plan generated.")
            return

        files = plan.get("files", [])

        print("\n📦 Files Planned:")
        for f in files:
            print(" →", f["path"])

        # =====================================
        # WRITE FILES
        # =====================================
        for file in files:
            print("📝 Writing:", file["path"])
            Executor.execute("write_file", file)

        print("\n✅ All Files Written.")

        # =====================================
        # AUTO TEST
        # =====================================
        tests_passed = self.auto_test()

        # =====================================
        # AUTO GIT PUSH IF TEST PASS
        # =====================================
        if tests_passed:
            self.auto_git_push()
        else:
            print("❌ Tests failed — Skipping Git Push")

    # =====================================
    # AUTO API TEST
    # =====================================
    def auto_test(self):

        print("\n🔎 Running Auto API Tests...")

        try:
            health = requests.get(
                "http://localhost:8000/health",
                timeout=5
            )

            metrics = requests.get(
                "http://localhost:8000/metrics",
                timeout=5
            )

            print("Health:", health.text)
            print("Metrics:", metrics.text)

            if health.status_code == 200 and metrics.status_code == 200:
                print("✅ API Tests Passed")
                return True

            print("❌ API Tests Failed")
            return False

        except Exception as e:
            print("❌ API Test Error:", e)
            return False

    # =====================================
    # AUTO GIT PUSH
    # =====================================
    def auto_git_push(self):

        print("\n🚀 Auto Git Commit + Push Started")

        try:
            commands = [
                "git add .",
                'git commit -m "Auto Generated Project"',
                "git push"
            ]

            for cmd in commands:
                print("Executing:", cmd)

                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True
                )

                print(result.stdout)
                print(result.stderr)

            print("✅ Auto Git Push Completed")

        except Exception as e:
            print("❌ Git Push Failed:", e)