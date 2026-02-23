import os
import subprocess
from app.config import settings


class Tools:

    @staticmethod
    def write_file(path: str, content):
        """
        Safe file writer.
        Accepts string OR list.
        Converts list → string automatically.
        """

        full_path = os.path.join(settings.WORKSPACE, path)
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)

        # Convert list to string
        if isinstance(content, list):
            content = "\n".join(map(str, content))

        # Convert anything else to string
        if not isinstance(content, str):
            content = str(content)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✅ File written: {path}"

    @staticmethod
    def read_file(path: str):
        full_path = os.path.join(settings.WORKSPACE, path)

        if not os.path.exists(full_path):
            return "❌ File does not exist."

        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def run_shell(command: str):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=settings.WORKSPACE,
                timeout=30
            )
            return result.stdout + result.stderr
        except Exception as e:
            return str(e)