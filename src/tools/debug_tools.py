import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(".").resolve()

def _safe_path(path):
    full_path = (WORKSPACE_ROOT / path).resolve()

    if not str(full_path).startswith(str(WORKSPACE_ROOT)):
        raise Exception("⚠️ Unsafe path detected")

    return full_path


def run_python_file(path):
    """
    Runs a Python file and captures stdout + stderr.
    Used for autonomous debugging.
    """

    path = _safe_path(path)

    if not path.exists():
        return f"❌ File not found: {path}"

    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True
        )

        output = result.stdout
        errors = result.stderr

        if result.returncode == 0:
            return f"✅ Program executed successfully\n\nOUTPUT:\n{output}"

        else:
            return f"❌ Program crashed\n\nERROR:\n{errors}"

    except Exception as e:
        return f"Execution error: {e}"