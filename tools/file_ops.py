from pathlib import Path

WORKSPACE = Path("workspace")

def safe_write(path, content):
    path = Path(path)

    if not path.is_absolute():
        path = WORKSPACE / path

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[write_file] → {path}")
