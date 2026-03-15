# src/shared_embeddings.py

import logging
from sentence_transformers import SentenceTransformer

# Reduce HuggingFace logging
logging.getLogger("transformers").setLevel(logging.ERROR)

# Load once globally
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

print("✅ Shared embedding model loaded")