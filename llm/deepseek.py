import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-coder:6.7b"

def call_llm(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["response"]
