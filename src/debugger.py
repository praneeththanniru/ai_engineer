from llm_router import debugger

def fix_code(code, error):

    prompt = f"""
Fix the following Python code.

Error:
{error}

Code:
{code}
"""

    return debugger(prompt)
