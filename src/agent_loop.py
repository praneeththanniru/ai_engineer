# src/agent_loop.py
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Allow agent to access project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from shared_embeddings import embedding_model
from codebase_rag import load_project_files, build_index, search_code

print(id(embedding_model))

from task_filter import filter_tasks
from llm_router import architect, coder, debugger, quick_edit
from agents.architect import design_architecture
from tools.file_tools import read_file, write_file, append_file, delete_file, move_file, list_dir
from tools.debug_tools import run_python_file

import json
import re
import requests
import time
import socket
import hashlib
import psutil
import subprocess
from bs4 import BeautifulSoup

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
def fetch_web_content(url):
    """
    Fetch a webpage and return clean text using BeautifulSoup.
    Limited to 5000 characters to avoid huge data.
    """
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text()[:5000]  # limit to 5000 chars
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return ""
# ========================== RESEARCH SYSTEM ==========================
def research_topic(query):
    print(f"\n🔎 Researching: {query}\n")
    links = search_web(query)
    research_data = []
    for link in links:
        page = fetch_web_content(link)
        if page:
            research_data.append({"url": link, "content": page})
    return research_data

# ========================== FLASK APP CONTEXT ==========================
app = create_app()
app.app_context().push()

# ========================== CONFIG ==========================
MODEL = "deepseek-r1:8b"
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

# ========================== WEB RESEARCH HELPER ==========================
def web_search(query, max_results=5):
    """
    Perform a simple web search using DuckDuckGo and return top URLs
    """
    print(f"🔍 Performing web search for: {query}")
    try:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        r = requests.get(url, params=params, timeout=10)
        links = re.findall(r'href="(https?://[^"]+)"', r.text)
        clean_links = [l for l in links if "duckduckgo.com" not in l]
        return clean_links[:max_results]
    except Exception as e:
        print("⚠️ Web search failed:", e)
        return []

def fetch_web_content(url):
    try:
        r = requests.get(url, timeout=20)
        # Use BeautifulSoup for reliable HTML parsing
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text()[:5000]  # limit to 5000 characters
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return ""

def research_topic(query):
    """
    Perform full research: search + fetch content
    """
    print(f"\n🔎 Researching: {query}\n")
    links = web_search(query)
    data = []
    for link in links:
        content = fetch_web_content(link)
        if content:
            data.append({"url": link, "content": content})
    return data


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

REFLECTION_PROMPT = """
You are the reflection agent.

Analyze the completed programming task.

Return JSON only.

Format:
{
 "success": true,
 "improvement": "what should be improved"
}
"""

GOAL_GENERATOR_PROMPT = """
You are the autonomous goal generator.

Analyze the project and suggest improvement goals.

Return JSON only.

Format:
{
 "goals": ["goal1", "goal2"]
}
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
        
# ========================== VECTOR MEMORY (placeholder) ==========================
VECTOR_MEMORY_FILE = BASE_DIR / "vector_memory.json"
VECTOR_INDEX = {}  # dictionary of {hash: vector_data} for now

def save_vector_memory(entry):
    import hashlib
    key = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    VECTOR_INDEX[key] = entry
    VECTOR_MEMORY_FILE.write_text(json.dumps(list(VECTOR_INDEX.values()), indent=2))

def load_vector_memory():
    global VECTOR_INDEX
    try:
        entries = json.loads(VECTOR_MEMORY_FILE.read_text())
        VECTOR_INDEX = {}
        for e in entries:
            import hashlib
            key = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
            VECTOR_INDEX[key] = e
    except:
        VECTOR_INDEX = {}
    return list(VECTOR_INDEX.values())        
        
# ========================== PROJECT STATE ==========================
def load_project_state():
    try:
        return json.loads(PROJECT_STATE_FILE.read_text())
    except:
        return {}

def save_project_state(state):
    PROJECT_STATE_FILE.write_text(json.dumps(state, indent=2))
    
    
# ========================== GOAL QUEUE ==========================
GOAL_QUEUE_FILE = WORKSPACE / "goal_queue.json"

# Ensure file exists
if not GOAL_QUEUE_FILE.exists():
    GOAL_QUEUE_FILE.write_text("[]")

def load_goal_queue():
    try:
        return json.loads(GOAL_QUEUE_FILE.read_text())
    except:
        return []

def save_goal_queue(goals):
    GOAL_QUEUE_FILE.write_text(json.dumps(goals, indent=2))

def add_goal(goal):
    goals = load_goal_queue()
    if goal not in goals:   # avoid duplicates
        goals.append(goal)
        save_goal_queue(goals)
    

# ========================== TASK SYSTEM ==========================
# Ensure TASK_FILE exists
if not TASK_FILE.exists():
    TASK_FILE.write_text("[]")

def load_tasks():
    try:
        return json.loads(TASK_FILE.read_text())
    except:
        return []

def save_tasks(tasks):
    TASK_FILE.write_text(json.dumps(tasks, indent=2))

def add_task(task):
    tasks = load_tasks()
    if task not in tasks:   # avoid duplicate tasks
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
    Call Ollama LLM and return response text.
    Includes caching and retry logic.
    """

    cache = load_cache()
    key = prompt_hash(prompt)

    # Cache check
    if key in cache and not DEBUG_ONLY:
        print("⚡ Using cached LLM response")
        return cache[key]

    payload = {
        "model": MODEL,
        "prompt": f"You are a helpful AI assistant. Always reply in English unless the user asks for another language.\n\nUser: {prompt}\nAssistant:",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_ctx": 8192,
            "num_thread": 4,
            "num_predict": 2048
        }
    }

    for attempt in range(retries):

        try:
            r = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=120
            )

            r.raise_for_status()

            result = r.json()
            response = result.get("response", "").strip()

        except requests.exceptions.RequestException as e:
            print("❌ Ollama request failed:", e)
            time.sleep(2)
            continue

        if not response or len(response) < 5:
            print(f"⚠️ Empty response, retry {attempt+1}/{retries}")
            time.sleep(2)
            continue

        # Save to cache
        cache[key] = response
        save_cache(cache)

        return response

    print("❌ LLM failed after retries")
    return ""


# ========================== JSON EXTRACTION ==========================
def extract_json(text: str) -> dict:
    import json, re
    from ast import literal_eval

    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid model response")

    # Remove Markdown or code fences
    text = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()

    # Try normal JSON load first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: find first {...} object in text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")

    candidate = text[start:end + 1]

    # Escape content fields safely
    def fix_content(match):
        raw = match.group(1)
        raw = raw.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
        return f'"content": "{raw}"'

    candidate = re.sub(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', fix_content, candidate, flags=re.DOTALL)
    candidate = candidate.replace("\t", "    ")

    # Final attempt: JSON or literal_eval
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
    """
    Safely writes files to the WORKSPACE folder.
    Ignores unsafe paths or malformed entries.
    """
    for f in files:
        if not isinstance(f, dict):
            continue
        if "path" not in f or "content" not in f:
            continue

        path = (WORKSPACE / f["path"]).resolve()
        if not str(path).startswith(str(WORKSPACE.resolve())):
            print(f"⚠️ Blocked unsafe file path: {path}")
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        content = f["content"].replace("\\n", "\n")
        path.write_text(content)
        print(f"📄 Created: {path}")

# ========================== WORKSPACE / PROJECT ==========================
def scan_workspace():
    """
    Returns a dictionary of {relative_path: content_snippet}.
    Shows first 2000 characters for each file.
    """
    state = {}
    for path in WORKSPACE.rglob("*"):
        if path.is_file():
            try:
                content = path.read_text()[:2000]
            except:
                content = "UNREADABLE FILE"
            state[str(path.relative_to(WORKSPACE))] = content
    return state


def summarize_workspace():
    """
    Summarizes workspace files and detects frameworks used.
    """
    files, frameworks = [], set()
    for path in WORKSPACE.rglob("*"):
        if path.is_file():
            files.append(str(path.relative_to(WORKSPACE)))
            try:
                content = path.read_text()[:2000]
            except:
                continue
            if "Flask(" in content: frameworks.add("Flask")
            if "FastAPI(" in content: frameworks.add("FastAPI")
            if "Django" in content: frameworks.add("Django")
    return {"files": files, "frameworks": list(frameworks)}


def build_project_tree():
    """
    Returns all files/folders in workspace as a sorted list.
    """
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
    """
    Runs a list of commands safely in WORKSPACE.
    Handles Flask apps, leftover processes, and errors.
    Returns error string if a command fails, else None.
    """

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

            if cmdline and any(str(WORKSPACE) in c for c in cmdline):
                if "python" in proc.info["name"].lower():

                    if flask_process is None or flask_process.pid != proc.info["pid"]:
                        print(f"🛑 Killing leftover process PID {proc.info['pid']}: {' '.join(cmdline)}")
                        proc.kill()

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # --- Step 2: Launch Flask if needed ---
    for f in files:

        content = f.get("content", "")

        if "Flask(__name__)" in content and (flask_process is None or flask_process.poll() is not None):

            port = find_free_port()
            temp_path = WORKSPACE / f["path"]

            if "app.run" not in content:

                flask_code = content + f'\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port={port})\n'

            else:

                flask_code = re.sub(
                    r'app\.run\([^\)]*\)',
                    f'app.run(host="0.0.0.0", port={port})',
                    content
                )

            temp_path.write_text(flask_code)

            print(f"\n🚀 Launching Flask server on port {port}...\n")

            flask_process = subprocess.Popen(
                ["python3", str(temp_path)],
                cwd=WORKSPACE
            )

            time.sleep(2)

            routes = re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"]\)', flask_code)

            for route in routes:
                print(f"🌐 Flask app running at http://127.0.0.1:{port}{route}")

    # --- Step 3: Run safe commands ---
    for cmd in cmds:

        if DEBUG_ONLY:
            print("⚙️ Skipping command (DEBUG_ONLY mode):", cmd)
            continue

        if not is_safe_command(cmd):
            continue

        # Skip running Flask app again
        if any(
            f.get("content", "").startswith("from flask")
            and cmd.endswith(f["path"])
            for f in files
        ):
            continue

        print(f"\n⚙️ Running command: {cmd}\n")

        try:

            result = subprocess.run(
                cmd,
                shell=True,
                cwd=WORKSPACE,
                timeout=300,
                capture_output=True,
                text=True
            )

            # ---- SUCCESS ----
            if result.returncode == 0:

                print("✅ Command executed successfully\n")

                if result.stdout:
                    print("OUTPUT:")
                    print(result.stdout)

            # ---- CRASH ----
            else:

                print("❌ Command crashed\n")

                if result.stderr:
                    print("ERROR:")
                    print(result.stderr)

                    # Attempt auto-debug if python script
                    try:

                        parts = cmd.strip().split()

                        if len(parts) >= 2 and parts[0] in ["python", "python3"]:

                            file_path = parts[1]

                            if file_path.endswith(".py"):
                                auto_debug(file_path, result.stderr)

                    except Exception as e:
                        print(f"⚠️ Debug trigger failed: {e}")

                return result.stderr

        except subprocess.TimeoutExpired:

            error = f"⚠️ Command timed out: {cmd}"

            print(error)

            return error

    return None


# ========================== AGENT LOOP ==========================
def run_goal(goal):
    """
    Execute an autonomous goal:
    - Architect designs structure
    - Planner creates tasks
    - Coder implements
    - Debugger fixes errors
    - Reflection + Research + Goal generation
    """
    global goal_count
    MAX_GOALS = 3  # Maximum number of autonomous improvement goals
    if "goal_count" not in globals():
        goal_count = 0

    if goal_count >= MAX_GOALS:
        print("🛑 Goal limit reached. Skipping further goals.")
        return

    from planner import create_plan
    from task_filter import filter_tasks
    from task_deduplicator import deduplicate_tasks
    from dependency_graph import build_dependency_graph

    save_tasks([])

    # ===== Virtual Environment Handling =====
    def setup_virtualenv():
        import subprocess
        venv_path = WORKSPACE / ".venv"
        python_exec = str(venv_path / "bin" / "python") if os.name != "nt" else str(venv_path / "Scripts" / "python.exe")

        if not venv_path.exists():
            print("🛠 Creating virtual environment...")
            subprocess.run(["python3", "-m", "venv", str(venv_path)], check=True)
            print(f"✅ Virtual environment created at {venv_path}")
        else:
            print(f"✅ Virtual environment already exists at {venv_path}")

        return python_exec, venv_path

    # ===== Automatic Dependency Installation =====
    def install_python_dependencies(python_exec):
        import subprocess
        import pkg_resources

        req_file = WORKSPACE / "requirements.txt"
        if req_file.exists():
            print(f"📦 Installing Python packages from {req_file.name}")
            subprocess.run([python_exec, "-m", "pip", "install", "-r", str(req_file)], check=True)
            return

        py_files = list(WORKSPACE.glob("*.py"))
        all_imports = set()
        for f in py_files:
            with open(f) as file:
                for line in file:
                    match = re.match(r"^\s*(?:import|from)\s+([\w_]+)", line)
                    if match:
                        all_imports.add(match.group(1))

        installed_packages = {pkg.key for pkg in pkg_resources.working_set}
        missing = [pkg for pkg in all_imports if pkg.lower() not in installed_packages]

        if missing:
            print(f"📦 Installing missing Python packages: {missing}")
            subprocess.run([python_exec, "-m", "pip", "install", *missing], check=True)
        else:
            print("✅ All Python dependencies are already installed.")

    def install_npm_dependencies():
        import subprocess
        package_json = WORKSPACE / "package.json"
        if package_json.exists():
            print(f"📦 Installing npm packages from {package_json.name}")
            subprocess.run(["npm", "install"], cwd=str(WORKSPACE), check=True)
        else:
            print("✅ No npm dependencies found.")

    python_exec, venv_path = setup_virtualenv()
    try:
        install_python_dependencies(python_exec)
    except Exception as e:
        print("⚠️ Python dependency installation failed:", e)

    try:
        install_npm_dependencies()
    except Exception as e:
        print("⚠️ npm dependency installation failed:", e)
        
    # ===== Step 30: Automated Code Style / Linting =====
    def run_code_linter(python_exec):
        import subprocess

        # ---- Python Linting (flake8) ----
        py_files = list(WORKSPACE.glob("*.py"))
        if py_files:
            print("🔍 Running Python linter (flake8)...")
            try:
                subprocess.run([python_exec, "-m", "pip", "install", "flake8", "black"], check=True)
                subprocess.run([python_exec, "-m", "flake8"] + [str(f) for f in py_files], check=True)
                # Optional: auto-format with Black
                subprocess.run([python_exec, "-m", "black"] + [str(f) for f in py_files], check=True)
                print("✅ Python linting and formatting completed.")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Python linting/formatting failed: {e}")

        # ---- JavaScript Linting (ESLint) ----
        package_json = WORKSPACE / "package.json"
        if package_json.exists():
            print("🔍 Running JS linter (ESLint)...")
            try:
                subprocess.run(["npm", "install", "-g", "eslint", "prettier"], check=True)
                subprocess.run(["eslint", "--fix", str(WORKSPACE)], check=True)
                print("✅ JS linting and formatting completed.")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ JS linting/formatting failed: {e}")

    # ---- Execute linter after dependencies installed ----
    run_code_linter(python_exec)
    
    
    # ===== Automatic Test Detection and Execution =====
    def run_tests(python_exec=None):
        import subprocess
        test_results = []

        # ---- Python tests ----
        py_tests = list(WORKSPACE.glob("test_*.py")) + list(WORKSPACE.glob("*_test.py"))
        for test_file in py_tests:
            print(f"🧪 Running Python test: {test_file.name}")
            cmd = [python_exec, "-m", "unittest", str(test_file)] if python_exec else ["python3", "-m", "unittest", str(test_file)]
            try:
                subprocess.run(cmd, cwd=str(WORKSPACE), check=True)
                test_results.append({"file": str(test_file), "success": True})
            except subprocess.CalledProcessError:
                test_results.append({"file": str(test_file), "success": False})

        # ---- JavaScript tests ----
        js_test_files = list(WORKSPACE.glob("**/*.test.js")) + list(WORKSPACE.glob("**/__tests__/*.js"))
        for js_test in js_test_files:
            print(f"🧪 Running JS test: {js_test.name}")
            try:
                subprocess.run(["npm", "test", str(js_test)], cwd=str(WORKSPACE), check=True)
                test_results.append({"file": str(js_test), "success": True})
            except subprocess.CalledProcessError:
                test_results.append({"file": str(js_test), "success": False})

        return test_results

    # ===== Architect Agent =====
    architecture = design_architecture(goal, coder)
    if architecture:
        print("\n🏗 Architect designed project structure:\n")
        print(architecture)

    # ===== Planner =====    
    tasks = create_plan(goal)
    tasks = filter_tasks(tasks)
    tasks = deduplicate_tasks(tasks)
    save_tasks(tasks)
    tasks = load_tasks()

    # ===== Step 31: Intelligent Task Prioritization =====
    def prioritize_tasks(tasks, past_vector_memory):
        """
        Reorder tasks based on:
        - Dependency graph (tasks needed first)
        - Past failures (retry tasks that previously failed)
        - Urgency heuristics (keyword-based)
        """
        from collections import defaultdict

        # Example: assign priority score to each task
        scores = defaultdict(int)
        dependency_graph = build_dependency_graph(WORKSPACE)

        for task in tasks:
            # Base score for dependencies
            deps = dependency_graph.get(task, [])
            scores[task] += len(deps)

            # Penalize tasks with past failures
            for past in past_vector_memory:
                if task.lower() in past.get("task", "").lower():
                    if not past.get("reflection", {}).get("success", True):
                        scores[task] += 5  # boost priority to retry failed tasks

            # Heuristic: tasks with "critical", "important", or "error" get higher priority
            if any(k in task.lower() for k in ["critical", "important", "error"]):
                scores[task] += 3

        # Sort tasks descending by score (higher score = higher priority)
        tasks_sorted = sorted(tasks, key=lambda t: scores[t], reverse=True)
        print("🔀 Tasks reordered based on priority and past insights:")
        for t in tasks_sorted:
            print(f"  - {t} (priority: {scores[t]})")
        return tasks_sorted

    # Apply prioritization
    tasks = prioritize_tasks(tasks, load_vector_memory())
    save_tasks(tasks)
    
    # ===== Task Execution Loop with Proactive Prioritization =====
    
    # Load past task history from vector memory
    past_tasks = load_vector_memory()
    
    # Shared context for dependency graph, research, etc.
    shared_context = {}
    
    while tasks:

        # --- Step 1: Assign priority to each task ---
        prioritized_tasks = []
        for t in tasks:
            score = 0
        
            # High priority if task previously failed
            past_failures = [pt for pt in past_tasks if pt.get("task", "").lower() == t.lower() and not pt.get("reflection", {}).get("success", True)]
            if past_failures:
                score += 20  # weight for failed tasks

            # Increase priority if task has dependencies (dependent tasks should run first)
            dep_graph = shared_context.get("dependency_graph", {})
            if t in dep_graph.get("depends_on", {}):
                score += 10

            # Increase priority if task has research available
            research = [r for r in shared_context.get("research_data", []) if t.lower() in r.get("topic", "").lower()]
            if research:
                score += 5

            # Default base score
            score += 1
        
            prioritized_tasks.append((score, t))

        # --- Step 2: Sort tasks by descending priority ---
        prioritized_tasks.sort(reverse=True, key=lambda x: x[0])
        tasks = [t for _, t in prioritized_tasks]
        save_tasks(tasks)

        # --- Step 3: Pop the highest priority task ---
        task = tasks.pop(0)
        save_tasks(tasks)
        print(f"\n🧩 Executing prioritized task: {task}\n")    

        # ===== Knowledge Context =====
        knowledge_context = query_knowledge(task)

        # ===== Shared Context for Multi-Agent Collaboration =====
        shared_context = {
            "task": task,
            "knowledge_context": knowledge_context,
            "project_tree": build_project_tree(),
            "memory_state": load_memory(),
            "recent_vector_memory": load_vector_memory(),
            "workspace_state": scan_workspace(),
            "dependency_graph": build_dependency_graph(WORKSPACE),
            "workspace_summary": summarize_workspace()
        }

        # ===== Research Insights (Web) =====
        research_data = []
        if "error" in task.lower() or "research" in task.lower():
            research_data = research_topic(task)
        shared_context["research_data"] = research_data

        # --- Query vector memory for similar past tasks ---
        past_tasks = load_vector_memory()
        similar_tasks = [t for t in past_tasks if task.lower() in t.get("task", "").lower()]
        if similar_tasks:
            print(f"🧠 Found {len(similar_tasks)} similar past tasks in memory. Reusing insights...")
            last_solution = similar_tasks[-1]
            knowledge_context += "\n\n# PAST TASK INSIGHTS:\n" + str(last_solution.get("reflection", ""))
            knowledge_context += "\n\n# PAST RESEARCH INSIGHTS:\n" + str(last_solution.get("research_data", ""))

        # ===== Full prompt for coder =====
        full_prompt = SYSTEM_PROMPT + f"""
TASK:
{shared_context['task']}

KNOWLEDGE BASE:
{shared_context['knowledge_context']}

PAST MEMORY:
{json.dumps(shared_context['memory_state'][-10:], indent=2)}

PROJECT STRUCTURE:
{json.dumps(shared_context['project_tree'], indent=2)}

DEPENDENCY GRAPH:
{json.dumps(shared_context['dependency_graph'], indent=2)}

WORKSPACE SUMMARY:
{json.dumps(shared_context['workspace_summary'], indent=2)}

CURRENT FILE CONTENT:
{json.dumps(shared_context['workspace_state'], indent=2)}

RECENT VECTOR MEMORY:
{json.dumps(shared_context['recent_vector_memory'][-5:], indent=2)}

RECENT RESEARCH INSIGHTS:
{json.dumps(shared_context['research_data'], indent=2)}

Return JSON only.
"""

        # ===== Coder Loop =====
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

        # ===== Write Files =====
        write_files(data.get("files", []))

        # ===== Run Commands =====
        error = run_commands(data.get("commands", []), data.get("files", []))

        # ===== Run tests =====
        test_results = run_tests(python_exec)
        shared_context["test_results"] = test_results
        for t in test_results:
            print(f"{'✅' if t['success'] else '❌'} Test result: {t['file']}")

        # ===== Reflection =====
        reflection_prompt = REFLECTION_PROMPT + f"""
TASK:
{task}

SHARED CONTEXT:
{json.dumps(shared_context, indent=2)}

Did the task succeed? Include test results in your evaluation. If not explain the improvement needed.
"""
        try:
            reflection_response = coder(reflection_prompt)
            reflection_data = extract_json(reflection_response)
            print("\n🧠 Reflection Result:")
            print(reflection_data)
        except:
            reflection_data = {"success": False, "improvement": "Reflection failed"}

        # ===== Smarter Reflection =====
        relevant_past_failures = [
            t for t in past_tasks
            if "success" in t.get("reflection", {}) and not t["reflection"]["success"]
               and task.lower() in t.get("task", "").lower()
        ]
        if relevant_past_failures:
            improvements = "\n".join([f"- {t['reflection'].get('improvement', '')}" for t in relevant_past_failures])
            knowledge_context += "\n\n# PAST ERROR INSIGHTS TO AVOID:\n" + improvements

        # ===== Save memory =====
        save_memory({"task": task, "reflection": reflection_data})

        # ===== Web Research / Vector Memory =====
        research_data = []
        if "error" in task.lower() or "research" in task.lower():
            research_data = research_topic(task)
            web_insights = ""
            for entry in research_data:
                web_insights += f"\n# {entry['url']}\n" + entry['content']
            knowledge_context += "\n\n# WEB RESEARCH INSIGHTS:\n" + web_insights

        vector_entry = {
            "task": task,
            "reflection": reflection_data,
            "workspace_state": scan_workspace(),
            "research_data": research_data,
            "timestamp": time.time()
        }
        save_vector_memory(vector_entry)

        # ===== Debug if error =====
        if error:
            print("\n🛠 Attempting automatic repair...\n")
            repair_prompt = DEBUGGER_PROMPT + f"""
TASK:
{task}

ERROR:
{error}

SHARED CONTEXT:
{json.dumps(shared_context, indent=2)}

RECENT RESEARCH INSIGHTS:
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
                    run_commands(repair_data.get("commands", []), repair_data.get("files", []))
                    print("✅ Repair attempt executed.\n")
                    break
                except:
                    time.sleep(2)
            else:
                print("❌ Automatic repair failed for this task.\n")
    
    # ===== Save goal completion + project snapshot =====
    save_memory({"goal_completed": goal})
    print("\n✅ Goal completed.\n")

    # --- Step 1: Prepare project snapshot ---
    project_snapshot = {
        "timestamp": time.time(),
        "goal": goal,
        "workspace_state": scan_workspace(),
        "dependency_graph": build_dependency_graph(WORKSPACE),
        "memory_state": load_memory(),
        "vector_memory": load_vector_memory(),
        "test_results": shared_context.get("test_results", []),
    }

    # --- Step 2: Save snapshot to file ---
    snapshot_dir = WORKSPACE / ".snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    snapshot_file = snapshot_dir / f"snapshot_{int(time.time())}.json"

    with open(snapshot_file, "w") as f:
        json.dump(project_snapshot, f, indent=2)

    print(f"💾 Project snapshot saved: {snapshot_file}")
    

    # ===== Smart Flask App Launch =====
    for file in WORKSPACE.glob("*.py"):
        content = file.read_text()
        if "from flask" in content or "@app.route" in content:
            print(f"\n🚀 Detected Flask app in {file.name}, launching automatically...")
            launch_flask_app(file.name)
            break

    # ===== Autonomous Goal Generator =====
    try:
        goal_prompt = GOAL_GENERATOR_PROMPT + f"""
PROJECT STRUCTURE:
{json.dumps(build_project_tree(), indent=2)}

Suggest improvements for this project.
"""
        goal_response = coder(goal_prompt)
        goal_data = extract_json(goal_response)
        for g in goal_data.get("goals", []):
            add_goal(g)
        print("🧠 Generated new improvement goals.")
    except Exception as e:
        print("⚠️ Goal generation failed:", e)

    # ===== Increment goal count =====
    goal_count += 1

# ========================== CHAT MODE ==========================
def chat_mode():
    global code_embeddings, code_files

    print("\n💬 Chat Mode (type 'exit' to leave)\n")

    while True:
        q = input("Question: ").strip()

        if q.lower() == "exit":
            print("👋 Leaving chat mode.\n")
            break

        if not q:
            print("⚠️ Please ask a question")
            continue

        try:
            # Search relevant code
            results = search_code(q, code_embeddings, code_files)

            context = "\n\n".join(
                f"FILE: {r['path']}\n{r['content'][:1500]}"
                for r in results
            )

            prompt = f"""
You are an AI coding assistant.

Use the project code below to answer the user's question.

PROJECT CODE:
{context}

USER QUESTION:
{q}
"""

            response = call_llm(prompt)

            print("\n🤖", response, "\n")

        except Exception as e:
            print("⚠️ Chat failed:", e)


# ========================== MAIN LOOP ==========================
def main():
    global goal_count

    print("\n🚀 Antigravity Autonomous Agent v16 — FULLY PRODUCTION READY\n")
    
    # ================= CODEBASE INDEX =================
    from codebase_rag import (
        load_project_files,
        build_index,
        save_index,
        load_index
    )

    global code_embeddings, code_files

    print("📚 Loading code index...")

    code_embeddings, code_files = load_index()

    if code_embeddings is None:

        print("⚙️ Building new code index...")

        project_files = load_project_files("src")

        code_embeddings, code_files = build_index(project_files)

        save_index(code_embeddings, code_files)

        print(f"✅ Indexed {len(project_files)} files and saved index\n")

    else:

        print(f"⚡ Loaded index with {len(code_files)} files\n")
    
    # Kill leftover servers
    cleanup_leftover_servers()

    goal_count = 0

    # -------- Mode selection --------
    mode = input("Mode (chat/dev): ").strip().lower()

    if mode == "chat":
        chat_mode()
        return

    print("\n🛠 Developer Agent Mode\n")

    while True:
        if goal_count >= 3:
            print("🛑 Maximum goal limit reached. Exiting main loop.")
            break

        try:
            goal = input("🎯 Enter goal (or 'exit'): ").strip()
        except EOFError:
            print("\n📌 No interactive input detected. Running default goal...\n")
            goal = "Create a Flask app with /hello route that returns {'message':'Hello from Antigravity Agent'} in JSON"

        if goal.lower() == "exit":
            break
        
        # ================= DEV TOOL COMMANDS =================

        if goal.startswith("read "):
            path = goal.replace("read ", "")
            print(read_file(path))
            continue

        if goal.startswith("write "):
            parts = goal.split(" ", 2)
            
            if len(parts) < 3:
                print("Usage: write <file> <content>")
                continue

            file_path = parts[1]
            content = parts[2]

            print(write_file(file_path, content))
            continue

        if goal.startswith("append "):
            parts = goal.split(" ", 2)

            if len(parts) < 3:
                print("Usage: append <file> <content>")
                continue

            file_path = parts[1]
            content = parts[2]

            print(append_file(file_path, content))
            continue

        if goal.startswith("delete "):
            path = goal.replace("delete ", "")
            print(delete_file(path))
            continue

        if goal.startswith("move "):
            parts = goal.split(" ")

            if len(parts) != 3:
                print("Usage: move <src> <dst>")
                continue

            print(move_file(parts[1], parts[2]))
            continue
        
        if goal == "ls":
            print(list_dir("."))
            continue

        if goal.startswith("ls "):
            path = goal[3:]
            print(list_dir(path))
            continue
        
        # ================= RUN PYTHON FILE =================

        if goal.startswith("run "):
            file_path = goal.replace("run ", "")
            
            error = run_python_file(file_path)
            print(error)
            
            # ✅ Auto-debug if crash detected
            if error and ("Traceback" in str(error) or "Error" in str(error)):
                auto_debug(file_path, error)
            
            continue
        
        # ================= NORMAL AGENT GOAL =================
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
        
# ========================== AUTO DEBUGGER ==========================
def auto_debug(file_path, error_message):
    """
    Uses the coder model to attempt to fix a crashing Python file.
    """

    print("\n🧠 Attempting automatic debugging...\n")

    try:
        code = read_file(file_path)
    except:
        print("⚠️ Could not read file for debugging.")
        return

    prompt = f"""
The following Python program crashed.

ERROR:
{error_message}

CODE:
{code}

Fix the code and return ONLY the full corrected Python file.
Do not explain anything.
"""

    fixed_code = coder(prompt)

    if fixed_code and len(fixed_code) > 20:
        write_file(file_path, fixed_code)
        print("✅ Agent rewrote the file with a possible fix")
    else:
        print("⚠️ Debugger could not generate a fix")        
    
# ========================== PROGRAM ENTRY / MAIN ==========================

if __name__ == "__main__":
    main()
   