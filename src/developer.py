# src/developer.py

from llm_router import coder


def write_code(task):

    prompt = f"""
Write Python code for this task.

Task:
{task}

Return only code.
"""

    return coder(prompt)
