from llm_router import developer

def write_code(task):

    prompt = f"""
Write Python code for this task.

Task:
{task}

Return only code.
"""

    return developer(prompt)
