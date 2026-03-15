import os
from pathlib import Path
import shutil

# Root workspace restriction (very important for safety)
WORKSPACE_ROOT = Path(".").resolve()

def _safe_path(path):
    """
    Ensure the path stays inside the project workspace.
    Prevents AI from editing system files.
    """
    full_path = (WORKSPACE_ROOT / path).resolve()

    if not str(full_path).startswith(str(WORKSPACE_ROOT)):
        raise Exception("⚠️ Unsafe path detected")

    return full_path


# ========================= READ FILE =========================

def read_file(path):
    path = _safe_path(path)

    if not path.exists():
        return f"File not found: {path}"

    try:
        return path.read_text()
    except Exception as e:
        return f"Read error: {e}"


# ========================= WRITE FILE =========================

def write_file(path, content):
    path = _safe_path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.write_text(content)
        return f"✅ File written: {path}"
    except Exception as e:
        return f"Write error: {e}"


# ========================= APPEND FILE =========================

def append_file(path, content):
    path = _safe_path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "a") as f:
            f.write(content)

        return f"✅ Content appended to {path}"

    except Exception as e:
        return f"Append error: {e}"


# ========================= DELETE FILE =========================

def delete_file(path):
    path = _safe_path(path)

    if not path.exists():
        return "File does not exist"

    try:
        path.unlink()
        return f"🗑 Deleted {path}"
    except Exception as e:
        return f"Delete error: {e}"


# ========================= MOVE FILE =========================

def move_file(src, dst):
    src = _safe_path(src)
    dst = _safe_path(dst)

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"📦 Moved {src} → {dst}"
    except Exception as e:
        return f"Move error: {e}"


# ========================= LIST DIRECTORY =========================

def list_dir(path="."):
    path = _safe_path(path)

    try:
        items = os.listdir(path)

        result = []
        for item in items:
            p = path / item

            if p.is_dir():
                result.append(f"[DIR] {item}")
            else:
                result.append(f"[FILE] {item}")

        return "\n".join(result)

    except Exception as e:
        return f"List error: {e}"
        