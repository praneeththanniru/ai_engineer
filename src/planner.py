from llm_router import architect
import re

def create_plan(goal):

    prompt = f"""
You are a task planner for a coding agent.

Rules:
- Generate ONLY the minimum steps needed.
- Maximum 4 tasks.
- Do NOT create web servers unless user explicitly asks.
- Do NOT install libraries unless required.
- Do NOT create documentation.
- Do NOT create unnecessary files.

Goal:
{goal}

Return numbered tasks.
"""

    response = architect(prompt)

    tasks = re.findall(r"\d+\.\s*(.*)", response)

    return tasks
