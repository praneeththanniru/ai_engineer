def deduplicate_tasks(tasks):

    seen = set()
    clean_tasks = []

    for task in tasks:
        t = task.lower().strip()

        if t not in seen:
            clean_tasks.append(task)
            seen.add(t)
        else:
            print(f"♻️ Removed duplicate task: {task}")

    return clean_tasks
