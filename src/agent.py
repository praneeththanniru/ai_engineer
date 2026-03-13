from task_filter import filter_tasks
from llm_router import architect, coder, debugger, quick_edit

#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Allow agent to access project root folders (rag, knowledge)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import json
import re
import requests
import time
import socket
import hashlib
import psutil  # Add this import at the top
import subprocess  # This allows Python to run terminal commands

# -------------------------- RAG Knowledge Brain --------------------------
from rag.rag_engine import query_knowledge

# ========================== SMART FLASK LAUNCH ==========================
LAST_FLASK_PORT = None  # remembers the last used port

def launch_flask_app(app_file: str):
    global flask_process, LAST_FLASK_PORT
    cleanup_leftover_servers()

    temp_path = WORKSPACE / app_file
    content = temp_path.read_text() if temp_path.exists() else ""

    if "@app.route('/')" not in content:
        content += "\n\nfrom flask import render_template\n@app.route('/')\ndef index():\n    return render_template('index.html')\n"

    templates_dir = WORKSPACE / "templates"
    templates_dir.mkdir(exist_ok=True)
    index_file = templates_dir / "index.html"
    if not index_file.exists():
        index_file.write_text("""
<!DOCTYPE html>
<html>
<head><title>Home</title></head>
<body>
<h1>Welcome to Antigravity Agent Flask App!</h1>
<p><a href="/login">Login</a></p>
</body>
</html>
""")
        print("📄 Created missing index.html")

    port = find_free_port()
    LAST_FLASK_PORT = port
    if "app.run" not in content:
        content += f'\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port={port})\n'
    else:
        import re
        content = re.sub(r'app\.run\([^\)]*\)', f'app.run(host="0.0.0.0", port={port})', content)

    temp_path.write_text(content)

    print(f"\n🚀 Launching Flask server on port {port}...\n")
    flask_process = subprocess.Popen([sys.executable, str(temp_path)], cwd=str(WORKSPACE))
    time.sleep(2)

    routes = re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"]\)', content)
    for route in routes:
        print(f"🌐 Flask app running at http://127.0.0.1:{port}{route}")
    print(f"💡 Test /hello with: curl http://127.0.0.1:{port}/hello")


# ========================== CLEANUP LEFTOVER SERVERS ==========================
def cleanup_leftover_servers():
    """
    Kill any running Python/Flask processes that belong to the workspace.
    Prevents 'Address already in use' errors.
    """
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            pid = proc.info["pid"]
            cmdline = proc.info["cmdline"]
            if cmdline and any(str(Path(PROJECT_ROOT / "src" / "workspace")) in c for c in cmdline):
                if "python" in proc.info["name"].lower():
                    print(f"🛑 Killing leftover process PID {pid}: {' '.join(cmdline)}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue



from backend.app import create_app, db
from backend.app.models import Task

# ========================== WEB SEARCH ==========================
def search_web(query, max_results=5):
    url = "https://duckduckgo.com/html/"
    params = {"q": query}
    try:
        r = requests.get(url, params=params, timeout=20)
        links = re.findall(r'href="(https?://[^"]+)"', r.text)
        clean_links = [l for l in links if "duckduckgo.com" not in l]
        return clean_links[:max_results]
    except Exception as e:
        print("⚠️ Search failed:", e)
        return []

# ========================== WEBPAGE FETCH ==========================
def fetch_page(url):
    try:
        r = requests.get(url, timeout=20)
        text = re.sub("<[^<]+?>", "", r.text)
        return text[:5000]
    except Exception:
        return ""

# ========================== RESEARCH SYSTEM ==========================
def research_topic(query):
    print(f"\n🔎 Researching: {query}\n")
    links = search_web(query)
    research_data = []
    for link in links:
        page = fetch_page(link)
        if page:
            research_data.append({"url": link, "content": page})
    return research_data

# ========================== FLASK APP CONTEXT ==========================
app = create_app()
app.app_context().push()

# ========================== CONFIG ==========================
DEBUG_ONLY = False  # True = skip running commands, False = execute
OLLAMA_URL = "http://localhost:11434/api/generate"

BASE_DIR = Path(__file__).parent
WORKSPACE = BASE_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)
MAX_RETRIES = 4

GOAL_QUEUE_FILE = BASE_DIR / "goal_queue.json"
CACHE_FILE = BASE_DIR / "llm_cache.json"
MEMORY_FILE = BASE_DIR / "memory.json"
TASK_FILE = BASE_DIR / "tasks.json"
PROJECT_STATE_FILE = BASE_DIR / "project_state.json"

for f in [GOAL_QUEUE_FILE, CACHE_FILE, MEMORY_FILE, TASK_FILE, PROJECT_STATE_FILE]:
    if not f.exists():
        f.write_text("[]" if f.suffix == ".json" and "cache" not in f.name and "project_state" not in f.name else "{}")


# ========================== SYSTEM PROMPT ==========================
SYSTEM_PROMPT = """
You are Antigravity Autonomous Coding Agent.

You MUST respond with VALID JSON ONLY. No markdown. No explanation. No backticks.

STRICT FORMAT:
{
  "plan": ["step1", "step2"],
  "files": [{"path": "hello.py","content": "print('Hello, World!')"}],
  "commands": ["python hello.py"]
}

Rules:
- Output ONLY a single raw JSON object
- Escape newlines as \\n inside content strings
- FULL working code only
- For Flask apps, always use host="0.0.0.0"
"""

# ========================== ROLE PROMPTS ==========================
PLANNER_PROMPT = """
You are the PLANNER agent.
Your job is to break a goal into clear programming tasks.
Return ONLY JSON with maximum 10 tasks.

Format:
{"tasks": ["task1", "task2"]}
"""

CODER_PROMPT = """
You are the CODER agent.
Implement code for the given task.
Return ONLY JSON with files and commands.

Format:
{"files":[{"path":"file.py","content":"code here"}],"commands":["python file.py"]}
"""

DEBUGGER_PROMPT = """
You are the DEBUGGER agent.
Fix broken code using the error message.
Return ONLY JSON with updated files and commands.

Format:
{"files":[{"path":"file.py","content":"fixed code"}],"commands":["python file.py"]}
"""

# ========================== CACHE SYSTEM ==========================
def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except:
        return {}

def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def prompt_hash(prompt):
    return hashlib.sha256(prompt.encode()).hexdigest()

# ========================== MEMORY SYSTEM ==========================

def save_memory(entry):
    try:
        memory = json.loads(MEMORY_FILE.read_text())
    except:
        memory = []

    memory.append(entry)

    MEMORY_FILE.write_text(json.dumps(memory, indent=2))


def load_memory():
    try:
        return json.loads(MEMORY_FILE.read_text())
    except:
        return []
        
# ========================== PROJECT STATE ==========================
def load_project_state():
    try:
        return json.loads(PROJECT_STATE_FILE.read_text())
    except:
        return {}

def save_project_state(state):
    PROJECT_STATE_FILE.write_text(json.dumps(state, indent=2))

# ========================== TASK SYSTEM ==========================
def load_tasks():
    try:
        return json.loads(TASK_FILE.read_text())
    except:
        return []

def save_tasks(tasks):
    TASK_FILE.write_text(json.dumps(tasks, indent=2))

def add_task(task):
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)

def generate_tasks(goal):
    prompt = PLANNER_PROMPT + f"\nGoal:\n{goal}\nReturn task list."
    response = architect(prompt)
    try:
        data = extract_json(response)
        tasks = data.get("tasks", [])[:10]
        for t in tasks:
            add_task(t)
    except Exception:
        print("⚠️ Could not generate tasks")

# ========================== LLM CALL ==========================
def call_llm(prompt: str, retries=5):
    """
    Call the LLM and return JSON-safe response.
    Auto-fixes broken JSON if needed.
    """
    cache = load_cache()
    key = prompt_hash(prompt)
    if key in cache and not DEBUG_ONLY:
        print("⚡ Using cached LLM response")
        return cache[key]

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9, "num_ctx": 8192, "num_thread": 4, "num_predict": 2048}
    }

    for attempt in range(retries):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=600)
            r.raise_for_status()
            response = r.json().get("response", "").strip()
        except requests.exceptions.RequestException as e:
            print("❌ Ollama request failed:", e)
            time.sleep(2)
            continue

        if not response or len(response) < 20:
            print(f"⚠️ Empty/short response, retry {attempt+1}/{retries}")
            time.sleep(2)
            continue

        # Try extracting JSON
        try:
            data = extract_json(response)
            cache[key] = response
            save_cache(cache)
            return response
        except ValueError:
            print(f"⚠️ Incomplete/broken JSON, attempt {attempt+1}/{retries}")
            time.sleep(2)
            continue

    print("❌ LLM failed after retries, returning empty dict")
    return "{}"


# ========================== JSON EXTRACTION ==========================
def extract_json(text: str) -> dict:
    import json, re
    from ast import literal_eval

    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid model response")

    text = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object detected in model response")

    candidate = text[start:end + 1]

    def fix_content(match):
        raw = match.group(1)
        raw = raw.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
        return f'"content": "{raw}"'

    candidate = re.sub(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', fix_content, candidate, flags=re.DOTALL)
    candidate = candidate.replace("\t", "    ")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        try:
            return literal_eval(candidate)
        except Exception:
            print("\n❌ MODEL OUTPUT COULD NOT BE FIXED\n")
            print(candidate)
            raise ValueError("Failed to extract JSON from LLM output")



# ========================== FILE SYSTEM ==========================
def write_files(files):
    for f in files:
        path = (WORKSPACE / f["path"]).resolve()
        if not str(path).startswith(str(WORKSPACE.resolve())):
            print("⚠️ Blocked unsafe file path")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f["content"].replace("\\n", "\n")
        path.write_text(content)
        print(f"📄 Created: {path}")

# ========================== WORKSPACE / PROJECT ==========================
def scan_workspace():
    state = {}
    for path in WORKSPACE.rglob("*"):
        if path.is_file():
            try: content = path.read_text()[:2000]
            except: content = "UNREADABLE FILE"
            state[str(path.relative_to(WORKSPACE))] = content
    return state

def summarize_workspace():
    files, frameworks = [], set()
    for path in WORKSPACE.rglob("*"):
        if path.is_file():
            files.append(str(path.relative_to(WORKSPACE)))
            try:
                content = path.read_text()[:2000]
            except: continue
            if "Flask(" in content: frameworks.add("Flask")
            if "FastAPI(" in content: frameworks.add("FastAPI")
            if "Django" in content: frameworks.add("Django")
    return {"files": files, "frameworks": list(frameworks)}

def build_project_tree():
    return sorted([str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*")])

# ========================== PORT & COMMANDS ==========================
def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

SAFE_COMMANDS = ["python","python3","pip","pip3","ls","pwd","mkdir","touch","echo","cat"]
BLOCKED_COMMANDS = ["rm","sudo","shutdown","reboot","mkfs","dd","kill","killall"]

def is_safe_command(cmd: str) -> bool:
    for b in BLOCKED_COMMANDS:
        if b in cmd.lower(): 
            print(f"❌ Blocked dangerous command: {cmd}")
            return False
    for s in SAFE_COMMANDS:
        if cmd.lower().startswith(s): return True
    print(f"⚠️ Unknown command blocked: {cmd}")
    return False


# ========================== COMMAND EXECUTION ==========================
def run_commands(cmds, files):
    import psutil
    import subprocess
    import time
    import re
    global flask_process

    if 'flask_process' not in globals():
        flask_process = None

    # --- Step 1: Kill leftover Flask/Python processes from previous runs ---
    print("🧹 Checking for leftover Flask/Python processes...")
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any(str(WORKSPACE) in c for c in cmdline) and "python" in proc.info["name"].lower():
                if flask_process is None or flask_process.pid != proc.info["pid"]:
                    print(f"🛑 Killing leftover process PID {proc.info['pid']}: {' '.join(cmdline)}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # --- Step 2: Launch Flask if needed ---
    for f in files:
        content = f.get("content", "")
        if "Flask(__name__)" in content and (flask_process is None or flask_process.poll() is not None):
            port = find_free_port()  # auto-pick free port
            temp_path = WORKSPACE / f["path"]

            # Make sure app.run has host=0.0.0.0 and correct port
            if "app.run" not in content:
                flask_code = content + f'\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port={port})\n'
            else:
                flask_code = re.sub(r'app\.run\([^\)]*\)', f'app.run(host="0.0.0.0", port={port})', content)

            temp_path.write_text(flask_code)
            print(f"\n🚀 Launching Flask server on port {port}...\n")
            flask_process = subprocess.Popen(["python3", str(temp_path)], cwd=WORKSPACE)
            time.sleep(2)  # give Flask time to start

            # Print all routes for easy access
            routes = re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"]\)', flask_code)
            for route in routes:
                print(f"🌐 Flask app running at http://127.0.0.1:{port}{route}")

    # --- Step 3: Run other safe commands ---
    for cmd in cmds:
        if DEBUG_ONLY:
            print("⚙️ Skipping command (DEBUG_ONLY mode):", cmd)
            continue
        if not is_safe_command(cmd):
            continue

        # Skip running python files that are Flask apps already launched
        if any(f.get("content", "").startswith("from flask") and cmd.endswith(f["path"]) for f in files):
            continue

        print(f"\n⚙️ Running command: {cmd}\n")
        try:
            result = subprocess.run(cmd, shell=True, cwd=WORKSPACE, timeout=300, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
                return result.stderr
        except subprocess.TimeoutExpired:
            error = f"Timeout while running command: {cmd}"
            print(error)
            return error

    return None


# ========================== AGENT LOOP ==========================

def run_goal(goal):

    from planner import create_plan
    from task_filter import filter_tasks
    from task_deduplicator import deduplicate_tasks
    from dependency_graph import build_dependency_graph

    save_tasks([])

    tasks = create_plan(goal)
    tasks = filter_tasks(tasks)
    tasks = deduplicate_tasks(tasks)

    save_tasks(tasks)
    tasks = load_tasks()

    while tasks:

        task = tasks.pop(0)
        save_tasks(tasks)

        print(f"\n🧩 Executing task: {task}\n")

        knowledge_context = query_knowledge(task)

        workspace_state = scan_workspace()
        workspace_summary = summarize_workspace()
        project_tree = build_project_tree()
        memory_state = load_memory()

        deps = build_dependency_graph(WORKSPACE)

        full_prompt = SYSTEM_PROMPT + f"""

KNOWLEDGE BASE:
{knowledge_context}

TASK:
{task}

PAST MEMORY:
{json.dumps(memory_state[-10:], indent=2)}

PROJECT STRUCTURE:
{json.dumps(project_tree, indent=2)}

DEPENDENCY GRAPH:
{json.dumps(deps, indent=2)}

WORKSPACE SUMMARY:
{json.dumps(workspace_summary, indent=2)}

CURRENT FILE CONTENT:
{json.dumps(workspace_state, indent=2)}

Return JSON only.
"""

        for attempt in range(MAX_RETRIES):

            response = coder(full_prompt)

            if not response:
                continue

            try:
                data = extract_json(response)
                break

            except:
                time.sleep(2)

        else:
            print("❌ Model failed task. Skipping.")
            continue

        write_files(data.get("files", []))

        error = run_commands(
            data.get("commands", []),
            data.get("files", [])
        )

        # ================= Reflection =================

        reflection_prompt = REFLECTION_PROMPT + f"""

TASK:
{task}

ERROR:
{error}

Did the task succeed? If not explain the improvement needed.
"""

        try:

            reflection_response = coder(reflection_prompt)
            reflection_data = extract_json(reflection_response)

            print("\n🧠 Reflection Result:")
            print(reflection_data)

        except:

            reflection_data = {
                "success": False,
                "improvement": "Reflection failed"
            }

        save_memory({
            "task": task,
            "reflection": reflection_data
        })

        # ================= Research if error =================

        research_data = []

        if error:
            research_data = research_topic(
                f"{task} python error {error}"
            )

        for g in data.get("goals", []):
            add_goal(g)

        # ================= Debug if error =================

        if error:

            print("\n🛠 Attempting automatic repair...\n")

            repair_prompt = DEBUGGER_PROMPT + f"""
TASK:
{task}

ERROR:
{error}

RESEARCH DATA:
{json.dumps(research_data, indent=2)}

Fix the code using the research information.

Return FULL JSON only.
"""

            for attempt in range(MAX_RETRIES):

                repair_response = debugger(repair_prompt)

                if not repair_response:
                    continue

                try:

                    repair_data = extract_json(repair_response)

                    write_files(repair_data.get("files", []))

                    run_commands(
                        repair_data.get("commands", []),
                        repair_data.get("files", [])
                    )

                    print("✅ Repair attempt executed.\n")

                    break

                except:

                    time.sleep(2)

            else:

                print("❌ Automatic repair failed for this task.\n")

    save_memory({
        "goal_completed": goal
    })

    print("\n✅ Goal completed.\n")
    
    # ===== Autonomous Goal Generator =====

goal_prompt = GOAL_GENERATOR_PROMPT + f"""
PROJECT STRUCTURE:
{json.dumps(build_project_tree(), indent=2)}

Suggest improvements for this project.
"""

try:
    goal_response = coder(goal_prompt)
    goal_data = extract_json(goal_response)

    for g in goal_data.get("goals", []):
        add_goal(g)

    print("🧠 Generated new improvement goals.")

except:
    print("⚠️ Goal generation failed.")


# ========================== MAIN LOOP ==========================
def main():
    print("\n🚀 Antigravity Autonomous Agent v16 — FULLY PRODUCTION READY\n")
    
    # ⚡ Kill leftover servers before running
    cleanup_leftover_servers()
    
    while True:
        try:
            state = load_project_state()
            if "current_goal" in state:
                print("\n🔄 Resuming previous project...\n")
                run_goal(state["current_goal"])
                return
            goals = load_goal_queue()
            if goals:
                goal = goals.pop(0)
                save_goal_queue(goals)
                print(f"\n🤖 Autonomous goal: {goal}")
            else:
                goal = input("🎯 Enter goal (or 'exit'): ").strip()
        except EOFError:
            print("\n📌 No interactive input detected. Running default goal...\n")
            goal = "Create a Flask app with /hello route that returns {'message':'Hello from Antigravity Agent'} in JSON"
        if goal.lower() == "exit": break
        run_goal(goal)

# ========================== TEST DB ==========================
def test_db():
    existing = Task.query.filter_by(name="Test Task from Agent").first()
    if not existing:
        task = Task(name="Test Task from Agent")
        db.session.add(task)
        db.session.commit()
    print("✅ Tasks in DB:")
    for t in Task.query.all():
        print(f"- {t.name} ({t.status})")


# -------------------------- File Helpers --------------------------

def write_file(path, content):
    """Create or overwrite a file with content."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"📄 Created file: {path}")

def append_file(path, content):
    """Append content to a file, or create it if missing."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write("\n" + content + "\n")
    print(f"📄 Appended to file: {path}")
   