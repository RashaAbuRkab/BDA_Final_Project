# OCR Support (Tesseract)
 
Documentation for the **real OCR** capability added to the RAG PDF Teaching Demo, and how it fits alongside the existing vision-LLM image captioning. This is a companion document to the main project `README.md` — read that first for the overall system; this one drills into the OCR addition specifically.
 
- **Backend:** FastAPI + LangChain + FAISS (unchanged)
- **New in this feature:** Tesseract OCR (via `pytesseract`) as a selectable, LLM-free alternative to vision-model image captioning

---

## Table of Contents
 
1. [What This Adds](#what-this-adds)
2. [Why OCR-Only Mode Exists](#why-ocr-only-mode-exists)
3. [Architecture Overview](#architecture-overview)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Runtime and Dependency Versions](#runtime-and-dependency-versions)
7. [Quick Start](#quick-start)
8. [How the OCR Pipeline Works](#how-the-ocr-pipeline-works)
9. [API Reference](#api-reference)
10. [Comparing OCR vs. Vision vs. Both](#comparing-ocr-vs-vision-vs-both)
11. [Teaching Flow](#teaching-flow)
12. [Troubleshooting](#troubleshooting)
13. [Core Message](#core-message)

---
    
## What This Adds

Previously, embedded images and scanned pages were only made searchable by sending them to a vision-capable LLM for captioning/transcription. This is not real OCR — it's a language model *describing* what it sees in an image.

This feature adds **actual OCR** via [Tesseract](https://github.com/tesseract-ocr/tesseract) (through the `pytesseract` Python wrapper), which uses classical character-recognition to extract text directly from images and rasterized scanned pages — no LLM call involved.

---

## Why OCR-Only Mode Exists

- **No LLM dependency** — ingestion works even if your vision model is unavailable, rate-limited, or misconfigured.
- **Faster and free** — Tesseract runs locally; no API calls, no cost, no network latency per image.
- **A fair comparison point** — lets you demonstrate classical OCR vs. vision-LLM transcription side-by-side on the same document.

---

## Architecture Overview
 
The OCR addition slots into the existing ingestion pipeline as a second (or exclusive) extraction path for non-text content:
 
```
PDF -> Text chunking (unchanged)
     -> Embedded image extraction (unchanged)
     -> Scanned-page detection (unchanged)
     -> [NEW] extraction_method routes each image to:
            - ocr_image()      (Tesseract, local, no LLM)
     -> Combined Document (OCR text and/or vision caption)
     -> Embeddings -> FAISS (unchanged)
```
 
Nothing about text chunking, embeddings, or the FAISS index structure changed — OCR is purely an alternate/additional source of text for the *image* documents that already existed in the pipeline.

 ---
 
## Project Structure
 
No new files were added — everything lives inside the existing backend files:
 
```text
rag-pdf-teaching-demo/
├── backend/
│   ├── main.py           # /upload now accepts extraction_method query param
│   ├── config.py         # + TESSERACT_CMD, OCR_LANGUAGES
│   ├── rag_service.py    # + ocr_image(), extraction_method logic in ingest_pdf()
│   ├── schemas.py        # + ocr_text, extraction_method fields on ChunkResponse
│   └── utils.py          # unchanged
├── frontend/
│   └── app.py
├── data/
│   └── uploads/images/   # unchanged — same folder holds extracted images either way
├── storage/
│   └── faiss_index/
├── .env                  # + TESSERACT_CMD, OCR_LANGUAGES
├── requirements.txt      # + pytesseract, Pillow
└── README.md
```

---
 
## Configuration
 
New settings added to `backend/config.py`:
 
```python
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or None
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "eng")
```
 
| Setting | Purpose | Default |
|---|---|---|
| `TESSERACT_CMD` | Path to the `tesseract` executable, if it's not on your system PATH (common on Windows) | `None` (relies on PATH) |
| `OCR_LANGUAGES` | Tesseract language code(s) to use, `+`-separated for multiple | `"eng"` |
 
New environment variables required in `.env` (only if Tesseract isn't on PATH, or you need a non-English language):
 
```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_LANGUAGES=eng
# For Arabic + English documents:
# OCR_LANGUAGES=eng+ara
```
 
> Note: `.env` is loaded at the top of `config.py`, before any `os.getenv()` calls in that file — so these values are available regardless of which module gets imported first.
 
---
 
## Runtime and Dependency Versions
 
In addition to the versions already listed in the main `README.md`:
 
### New Python packages
 
- `pytesseract` — Python wrapper around the Tesseract CLI
- `Pillow` — required to open images before handing them to `pytesseract`
### External (non-Python) dependency
 
- **Tesseract OCR engine** — this is a standalone binary, *not* installed via pip. `pytesseract` only calls out to it; if it isn't installed separately, every OCR call fails with `TesseractNotFoundError`.
  - Windows build: [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki) (e.g. `tesseract-ocr-w64-setup-<version>.exe`)
### Verify installed versions (optional)
 
```powershell
pip show pytesseract Pillow
tesseract --version
```
 
---
 
## Quick Start
 
### 1) Install the Tesseract engine
 
Download and run the Windows installer from the [UB-Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki).
 
- Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- During setup, check **"Add to system PATH"** if offered — saves you from needing `TESSERACT_CMD` at all.
- On the **"Additional Language Data"** screen, select any non-English languages you need (e.g. Arabic) so you don't have to re-run the installer later.
### 2) Install Python dependencies
 
```powershell
cd "D:\Workshop Material\Jupyter Notebooks\RAGApp\rag-pdf-teaching-demo"
pip install -r requirements.txt
```
Make sure `pytesseract` and `Pillow` are in `requirements.txt`.
 
### 3) Configure `.env`
 
```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_LANGUAGES=eng
```
 
### 4) Verify Tesseract is reachable
 
Run in the same Python environment as the backend (interactive shell or a throwaway script):
 
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
print(pytesseract.get_tesseract_version())
```
 
If this prints a version number, you're set. If it raises `TesseractNotFoundError`, the path doesn't match your actual install — check in File Explorer.
 
### 5) Run the backend as usual
 
```powershell
uvicorn backend.main:app --reload
```
 
### 6) Ingest a PDF using OCR only (the new default)
 
```
POST /upload
```
No parameters needed — `extraction_method` defaults to `"ocr"`.
 
---

## How the OCR Pipeline Works
 
Inside `ingest_pdf()`, for each extracted embedded image and each rasterized scanned page:
 
1. **If `extraction_method` is `"ocr"` :**
   `ocr_image()` opens the image with `PIL.Image` and runs `pytesseract.image_to_string(img, lang=OCR_LANGUAGES)`, returning the raw recognized text. If OCR fails for any reason, a short `(OCR failed: ...)` message is stored instead, and ingestion continues rather than aborting.
```
   [Image/Scanned content - Page N] (method: ocr)
 
   OCR Text:
   <extracted text>
```
   Its metadata stores `type: "image"`, `image_path`, `ocr_text`, and `extraction_method`.
 
2. This `Document` is embedded and added to the **same FAISS index** as the regular text chunks — retrieval doesn't distinguish between text-derived and image-derived content at query time; it's all just semantically searchable.
Because `caption_image()` is only called when `extraction_method` includes `"vision"`, choosing `"ocr"` guarantees **zero vision-LLM calls** for that upload — useful when the vision model is down, rate-limited, or you simply want a free/offline-friendly run.
 
---
 
## Troubleshooting
 
- **`TesseractNotFoundError` / "tesseract is not installed or it's not in your PATH"**
  → The Tesseract binary isn't installed, or `TESSERACT_CMD` in `.env` doesn't point to the right path. Verify with the check in [Quick Start step 4](#quick-start).
- **`.env` changes not taking effect**
  → Fully restart the backend process (not just `--reload`) after editing `.env` — `TESSERACT_CMD` and `OCR_LANGUAGES` are read once at startup, in `config.py`.
- **OCR text is empty or garbled**
  → Check `OCR_LANGUAGES` matches the document's actual language(s). OCR quality also depends on image resolution — scanned pages are rasterized at 200 DPI by default (`extract_scanned_pages`), which is usually sufficient, but very small source text may need a higher DPI.
- **Want Arabic (or other non-English) OCR support**
  → Make sure the relevant language pack was installed with Tesseract (select it during setup, or manually add e.g. `ara.traineddata` to the Tesseract `tessdata` folder), then set `OCR_LANGUAGES=eng+ara`.
- **Still seeing vision-model error messages after switching to `"ocr"`**
  → Confirm you're not explicitly passing `extraction_method=vision` or `extraction_method=both` — `"ocr"` mode never calls the vision LLM, so it cannot produce a vision-related error.
- **Dependency issues on Windows**
  → Activate your environment, run `pip install -r requirements.txt` again, and confirm `import pytesseract` and `from PIL import Image` both succeed without errors.
---
 
## Core Message
 
OCR and vision-LLM captioning solve the same problem — turning pixels into searchable text — through fundamentally different means: one recognizes character shapes directly, the other describes and transcribes using a language model's general understanding. Neither is strictly "better" in all cases, which is exactly why this project lets you run both side-by-side and compare.
