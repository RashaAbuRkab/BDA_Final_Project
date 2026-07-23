import os

UPLOAD_DIR = "data/uploads"
IMAGES_DIR = "data/uploads/images"
FAISS_INDEX_PATH = "storage/faiss_index"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 4

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None

# Embeddings model
EMBEDDING_MODEL = "openai/text-embedding-3-small" if OPENAI_BASE_URL else "text-embedding-3-small"

# Conversation/Vision Model
LLM_MODEL = "azure-openai/gpt-5" if OPENAI_BASE_URL else "gpt-4.1-mini"
VISION_MODEL = LLM_MODEL  # gpt-5 Supports multimodal image input
TEMPERATURE = 0