import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_model(model, prompt):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192
        }
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["response"]


def architect(prompt):
    return call_model("llama3.1:8b", prompt)


def coder(prompt):
    return call_model("qwen2.5-coder:14b", prompt)


def debugger(prompt):
    return call_model("deepseek-coder:6.7b", prompt)


def quick_edit(prompt):
    return call_model("qwen2.5-coder:7b", prompt)
