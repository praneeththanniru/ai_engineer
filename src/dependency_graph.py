import re
from pathlib import Path

def build_dependency_graph(workspace):

    graph = {}

    for file in Path(workspace).rglob("*.py"):

        try:
            content = file.read_text()
        except:
            continue

        imports = re.findall(r"import (\w+)", content)

        graph[file.name] = imports

    return graph
