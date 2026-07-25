import os
from dotenv import load_dotenv
load_dotenv()

UPLOAD_DIR = "data/uploads"
IMAGES_DIR = "data/uploads/images"
FAISS_INDEX_PATH = "storage/faiss_index"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 4
 
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or None

# Embeddings model
EMBEDDING_MODEL = "openai/text-embedding-3-small" if OPENAI_BASE_URL else "text-embedding-3-small"

# Conversation/Vision Model
LLM_MODEL = "gpt-4.1-mini"
VISION_MODEL = LLM_MODEL  # gpt-5 Supports multimodal image input
TEMPERATURE = 0
 
# OCR settings (real OCR via Tesseract, in addition to vision-model captioning)
# On Windows, point this at your tesseract.exe install if it's not on PATH, e.g.:
# TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or None
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "eng")