from sentence_transformers import SentenceTransformer
import chromadb
from pathlib import Path

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Setup Chroma DB
client = chromadb.Client()
collection = client.get_or_create_collection("knowledge")

KNOWLEDGE_DIR = Path("knowledge")

def index_knowledge():
    docs = []
    ids = []

    for file in KNOWLEDGE_DIR.glob("*.md"):
        text = file.read_text()
        docs.append(text)
        ids.append(file.name)

    if docs:
        embeddings = model.encode(docs).tolist()

        collection.upsert(
            documents=docs,
            embeddings=embeddings,
            ids=ids
        )

def query_knowledge(query):
    embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=3
    )

    docs = results.get("documents", [[]])[0]

    return "\n\n".join(docs)


# Index knowledge at startup
index_knowledge()
