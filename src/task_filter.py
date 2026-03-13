BLOCKED_TASKS = [
    "open editor",
    "close editor",
    "delete temp",
    "install flask",
    "install library",
    "setup environment",
    "open browser"
]

def filter_tasks(tasks):

    clean_tasks = []

    for task in tasks:
        task_lower = task.lower()

        blocked = False
        for b in BLOCKED_TASKS:
            if b in task_lower:
                blocked = True
                print(f"🚫 Filter removed task: {task}")
                break

        if not blocked:
            clean_tasks.append(task)

    return clean_tasks