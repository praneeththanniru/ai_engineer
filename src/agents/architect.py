ARCHITECT_PROMPT = """
You are the Architect Agent.

Your job is to design the project structure before coding begins.

Return JSON only.

Format:
{
 "architecture": {
   "folders": ["folder1", "folder2"],
   "files": ["file1.py", "file2.py"],
   "notes": "short explanation of architecture"
 }
}
"""

def design_architecture(goal, coder):

    prompt = ARCHITECT_PROMPT + f"""

USER GOAL:
{goal}

Design a clean software architecture for this project.
"""

    try:
        response = coder(prompt)

        import json
        import re

        json_match = re.search(r"\{.*\}", response, re.S)

        if json_match:
            data = json.loads(json_match.group())
            return data.get("architecture", {})

    except Exception as e:
        print("⚠️ Architect agent failed:", e)

    return {}