# src/codebase_rag.py

import os
import pickle
import numpy as np
from shared_embeddings import embedding_model

INDEX_FILE = "code_index.pkl"


# ===============================
# Load project files
# ===============================
def load_project_files(project_path):

    files = []

    for root, _, filenames in os.walk(project_path):

        for f in filenames:

            if f.endswith((".py", ".txt", ".md", ".json", ".html", ".css")):

                path = os.path.join(root, f)

                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()

                    files.append({
                        "path": path,
                        "content": content
                    })

                except Exception:
                    pass

    return files


# ===============================
# Build index
# ===============================
def build_index(files):

    texts = [
        f"FILE PATH: {f['path']}\n\n{f['content']}"
        for f in files
    ]

    embeddings = embedding_model.encode(texts)

    return embeddings, files


# ===============================
# Save index
# ===============================
def save_index(embeddings, files):

    with open(INDEX_FILE, "wb") as f:

        pickle.dump({
            "embeddings": embeddings,
            "files": files
        }, f)

    print("💾 Code index saved")


# ===============================
# Load index
# ===============================
def load_index():

    if not os.path.exists(INDEX_FILE):

        return None, None

    try:

        with open(INDEX_FILE, "rb") as f:

            data = pickle.load(f)

        print("📂 Loaded existing code index")

        return data["embeddings"], data["files"]

    except Exception:

        return None, None


# ===============================
# Search code
# ===============================
def search_code(query, embeddings, files, top_k=8):

    query_embedding = embedding_model.encode([query])[0]

    scores = []

    for i, emb in enumerate(embeddings):

        sim = np.dot(query_embedding, emb) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(emb)
        )

        scores.append((sim, i))

    scores.sort(reverse=True)

    results = [files[idx] for _, idx in scores[:top_k]]

    return results