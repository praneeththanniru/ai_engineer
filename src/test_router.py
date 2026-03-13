from llm_router import architect, coder, debugger, quick_edit

print("\n🧠 Testing Architect (llama3.1)...")
print(architect("Break down the goal: create hello world python app"))

print("\n👨‍💻 Testing Coder (qwen coder 14b)...")
print(coder("Write python hello world"))

print("\n🐞 Testing Debugger (deepseek)...")
print(debugger("Fix this python error: NameError name x not defined"))

print("\n⚡ Testing Quick Edit (qwen coder 7b)...")
print(quick_edit("Rewrite python hello world in one line"))
