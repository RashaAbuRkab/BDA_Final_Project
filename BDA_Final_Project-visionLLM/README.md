# RAG PDF Teaching Demo
 
Professional teaching/demo project for explaining how Retrieval-Augmented Generation (RAG) works with a single PDF — now including support for **embedded images, tables, and scanned pages**, not just plain text.

- **Backend:** FastAPI + LangChain + FAISS
- **Frontend:** Streamlit
- **Models:** OpenAI-compatible embeddings + chat model (text) + vision model (image/scanned-page captioning)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
5. [How the RAG Pipeline Works](#how-the-rag-pipeline-works)
6. [Multimodal Ingestion (Images & Scanned Pages)](#multimodal-ingestion-images--scanned-pages)
7. [API Reference](#api-reference)
8. [Frontend Behavior](#frontend-behavior)
9. [Teaching Flow](#teaching-flow)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The system is split into two services:

1. **Backend (FastAPI)**
   - Accepts PDF uploads
   - Chunks and embeds the document
   - Extracts embedded images and detects scanned (image-only) pages
   - Captions/transcribes those images with a vision-capable LLM
   - Stores text chunks + image captions together in a single FAISS index
   - Answers questions both with and without retrieval
2. **Frontend (Streamlit)**
   - UI for upload + question asking
   - Visual comparison:
     - **Without RAG** (general model answer)
     - **With RAG** (grounded answer from retrieved chunks)
   - Displays retrieved chunks with source/page/similarity score/**content type** (text vs. image)

Data flow:

`PDF -> Text chunking + Image extraction + Scanned-page detection -> Embeddings -> FAISS -> Retrieval -> Prompt -> LLM -> Answer`

---

## Project Structure

```text
rag-pdf-teaching-demo/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── rag_service.py
│   ├── schemas.py
│   └── utils.py
├── frontend/
│   └── app.py
├── data/
│   └── uploads/
│   └── uploads/images/        # extracted images + rasterized scanned pages, per document
├── storage/
│   └── faiss_index/
├── .env
├── requirements.txt
└── README.md
```

---

## Configuration

Runtime settings are defined in `backend/config.py`:

- `CHUNK_SIZE = 300`
- `CHUNK_OVERLAP = 50`
- `TOP_K = 4`
- `EMBEDDING_MODEL = "text-embedding-3-small"`
- `LLM_MODEL = "gpt-5"`
- `TEMPERATURE = 0`
- `UPLOAD_DIR = "data/uploads"`
- `IMAGES_DIR = "data/uploads/images"` — root folder for extracted images and rasterized scanned pages
- `FAISS_INDEX_PATH = "storage/faiss_index"`
- `OPENAI_BASE_URL` — base URL for the OpenAI-compatible API endpoint (lets the backend point at a custom/proxy endpoint instead of the default OpenAI API)

Environment variable required in `.env`:

```env
OPENAI_API_KEY=your_real_openai_api_key
```

---

## Runtime and Dependency Versions

Use the following versions for a stable run.

### Python

- `Python 3.13.12`

### Core packages

- `fastapi==0.136.0`
- `uvicorn==0.45.0`
- `streamlit==1.57.0`
- `requests==2.32.5`
- `python-multipart==0.0.26`
- `python-dotenv==1.2.1`
- `langchain==1.2.15`
- `langchain-openai==1.1.16`
- `langchain-community==0.4.1`
- `langchain-text-splitters==1.1.2`
- `faiss-cpu==1.13.2`
- `pypdf==6.10.2`

### Verify installed versions (optional)

```powershell
python --version
pip show fastapi uvicorn streamlit requests python-multipart python-dotenv langchain langchain-openai langchain-community langchain-text-splitters faiss-cpu pypdf
```

---

## Quick Start

### 1) Install dependencies

```powershell
cd "D:\Workshop Material\Jupyter Notebooks\RAGApp\rag-pdf-teaching-demo"
pip install -r requirements.txt
```

> Note: image extraction/rasterization requires `PyMuPDF` (`fitz`) in addition to the existing dependencies.

### 2) Run backend (Terminal 1)

```powershell
cd "D:\Workshop Material\Jupyter Notebooks\RAGApp\rag-pdf-teaching-demo"
uvicorn backend.main:app --reload
```

Expected backend URL:

- `http://localhost:8000`

Health check:

- [http://localhost:8000/health](http://localhost:8000/health)

### 3) Run frontend (Terminal 2)

```powershell
cd "D:\Workshop Material\Jupyter Notebooks\RAGApp\rag-pdf-teaching-demo"
streamlit run frontend/app.py
```

Expected frontend URL:

- `http://localhost:8501`

---

## How the RAG Pipeline Works

### A) Ingestion (`POST /upload`)

1. Upload PDF from frontend.
2. Backend saves file in `data/uploads`.
3. `PyPDFLoader` reads pages into documents.
4. `RecursiveCharacterTextSplitter` creates chunks (tagged `type="text"`).
5. Embedded images are extracted from the PDF (see below) and scanned (text-sparse) pages are rasterized to full-page images.
6. Each extracted image/scanned page is captioned by a vision LLM, and the caption becomes a retrievable `Document` (tagged `type="image"`).
7. Text chunks and image-caption documents are combined and embedded together with `OpenAIEmbeddings`.
8. `FAISS.from_documents(...)` builds a single vector index over both content types.
9. Index is persisted under `storage/faiss_index`.

### B) Question Answering (`POST /ask`)

For each question, backend runs two paths:

1. **Without RAG:** send question directly to LLM.
2. **With RAG:**
   - run `similarity_search_with_score(question, k=TOP_K)` across the combined text + image index
   - take top chunks + their similarity scores
   - build grounded prompt from retrieved chunks (each labeled with its source and page)
   - ask LLM to answer using only retrieved context

### Why similarity score is shown

Each retrieved chunk includes a score, so students can see ranking quality and understand:

**"The retriever ranks chunks by semantic similarity — regardless of whether the original content was text or an image."**

---

## Multimodal Ingestion (Images & Scanned Pages)
 
This is the main new capability added to the ingestion pipeline.

### Embedded image extraction
 
- For every page, embedded raster images are pulled out via PyMuPDF (`fitz`).
- Images smaller than 5 KB are skipped (filters out icons, bullets, and other decorative ornaments so they don't waste API calls).
- Extracted images are saved to `data/uploads/images/<document_name>/pageN_imgM.<ext>`.

### Scanned page detection
 
- Each page's extractable text length is checked against a threshold (default: 30 characters).
- Pages with little-to-no extractable text are treated as scanned/image-only pages and rasterized at 200 DPI to a full-page PNG.
- This catches pages that are pure images (e.g., scanned contracts, photographed tables) that the text loader would otherwise miss entirely.

### Vision captioning
 
- Every extracted image and rasterized scanned page is sent to a vision-capable chat model with an instruction to exhaustively transcribe all readable text, numbers, and table data (reproducing tables as labeled rows/values).
- The resulting transcription becomes the page content of a `Document`, stored with metadata:
  - `source`, `page`, `type: "image"`, `image_path`
- If captioning fails for a given image, a placeholder `"Undescribed image (failed: ...)"` is stored instead, so ingestion doesn't fail outright.

### Unified retrieval
 
- Text chunks and image-caption documents live in the *same* FAISS index, so a single similarity search can surface either type depending on which is more relevant to the question.
- The API response and frontend both surface a `type` field (`"text"` or `"image"`) and, for images, the `image_path` so the original image/scanned page can be traced back and displayed. 

## API Reference

### `GET /health`

Response:

```json
{"status":"ok"}
```

### `POST /upload`

Request:

- `multipart/form-data`
- field: `file` (PDF)

Response example:

```json
{
  "filename": "Employee-Handbook.pdf",
  "pages": 34,
  "chunks": 242,
  "images": 12,
  "message": "PDF indexed successfully"
}
```

### `POST /ask`

Request body:

```json
{"question":"What is the attendance policy?"}
```

Response fields:

- `question`
- `no_rag_answer`
- `rag_answer`
- `retrieved_chunks[]`:
  - `content`
  - `source`
  - `page`
  - `score`
  - `type` (`"text"` or `"image"`)
  - `image_path` (populated only when `type` is `"image"`)

---

## Frontend Behavior

The Streamlit app contains:

1. **RAG Flow diagram**
2. **Upload + index section** — now also reports how many images/scanned pages were indexed
3. **Comparison section**
   - Without RAG shown with `st.error(...)`
   - With RAG shown with `st.success(...)`
4. **Retrieved chunks section**
   - Displays source/page/content/`Similarity Score`/content type
   - For image-derived chunks, can show the extracted image/scanned page alongside its transcription

Backend URL used by frontend:

- `BACKEND_URL = "http://localhost:8000"` in `frontend/app.py`

---

## Teaching Flow

Recommended classroom order:

1. Upload a PDF (ideally one with at least one table/image and one scanned-looking page) and build the index.
2. Explain chunking and embeddings for text.
3. Explain image extraction, scanned-page detection, and vision captioning — the "multimodal" step.
4. Explain FAISS retrieval and ranking across the combined text + image index.
5. Ask a question that can only be answered from an image/table.
6. Compare no-RAG vs RAG answers.
7. Open retrieved chunks and inspect scores and content types (text vs. image).
8. Emphasize grounding, traceability, and how non-text content is made searchable.

---

## Troubleshooting

- **Frontend cannot call backend**
  - verify backend is running on `http://localhost:8000`
  - verify `BACKEND_URL` in `frontend/app.py`

- **No useful retrieved chunks**
  - re-index after changing chunk settings
  - adjust `TOP_K` for broader context

- **Dependency issues on Windows**
  - activate your environment
  - run `pip install -r requirements.txt` again


- **Images not being captioned / ingestion is slow**
  - large or image-heavy PDFs trigger many vision LLM calls; expect longer ingestion times
  - check that `OPENAI_BASE_URL` and API key are valid for vision requests
  - a failed caption doesn't stop ingestion — it's stored as `"Undescribed image (failed: ...)"`, which can also be a place to check if answers seem to be missing image-derived context

- **Scanned pages not detected**
  - adjust the `text_threshold` in `extract_scanned_pages` if pages with a small amount of text are being missed or incorrectly flagged
 
- **Dependency issues on Windows**
  - activate your environment
  - run `pip install -r requirements.txt` again
  - ensure `PyMuPDF` installed correctly (`import fitz` should succeed)
      
---

## Core Message

The LLM does **not** read the PDF directly.  
FAISS retrieves the most semantically relevant chunks first.  
The LLM generates the answer using retrieved context.
