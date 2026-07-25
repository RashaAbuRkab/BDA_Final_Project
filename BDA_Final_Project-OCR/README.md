# OCR Support (Tesseract) — Feature README

This document covers the **real OCR** capability added to the RAG PDF Teaching Demo, and how it fits alongside the existing vision-LLM image captioning.

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

## Setup

### 1. Install the Tesseract engine (not just the Python package)

`pytesseract` is only a wrapper — it calls out to a real Tesseract binary that must be installed separately.

**Windows:**
Download and run the installer from the [UB-Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki):
```
tesseract-ocr-w64-setup-<version>.exe
```
- Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- During setup, check **"Add to system PATH"** if offered.
- On the **"Additional Language Data"** screen, also select any non-English languages you need (e.g. Arabic).

### 2. Configure `.env`

```dotenv
# Only needed if tesseract.exe is not on your system PATH:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# OCR language(s) — Tesseract language codes, "+" separated for multiple:
OCR_LANGUAGES=eng
# For Arabic + English:
# OCR_LANGUAGES=eng+ara
```

### 3. Verify Tesseract is reachable

Run this in the same Python environment as the backend:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
print(pytesseract.get_tesseract_version())
```
If this prints a version number, you're set. If it raises `TesseractNotFoundError`, double-check the install path and `.env` value.

### 4. Python dependencies

Add to `requirements.txt`:
```
pytesseract
Pillow
```
(`Pillow` is required to open images before passing them to `pytesseract`.)

---

## Usage

### Ingest a PDF using OCR only (default)

```
POST /upload
```
No parameters needed — `extraction_method` defaults to `"ocr"`, so embedded images and scanned pages are processed with Tesseract only. The vision LLM is never called.
---

## How It Works Internally

For each extracted image / rasterized scanned page in `ingest_pdf()`:

1. If `extraction_method` is `"ocr"` → `ocr_image()` runs Tesseract (`pytesseract.image_to_string`) on the image and returns raw text.
2. The resulting text (OCR text) is combined into a single `Document`, tagged with `type: "image"` and `extraction_method` in its metadata, and embedded into the same FAISS index as the regular text chunks.

---

## Troubleshooting

- **`TesseractNotFoundError` / "tesseract is not installed or it's not in your PATH"**
  → Tesseract binary isn't installed, or `TESSERACT_CMD` in `.env` doesn't point to the right path. Verify with the check in step 3 above.

- **`.env` changes not taking effect**
  → Fully restart the backend process (not just a hot-reload) after editing `.env` — `TESSERACT_CMD` is read once at startup.

- **OCR text is empty or garbled**
  → Check `OCR_LANGUAGES` matches the document's language(s). Also, OCR quality depends on image resolution — scanned pages are rasterized at 200 DPI by default (`extract_scanned_pages`), which is usually sufficient, but very small source text may need a higher DPI.

- **Want Arabic OCR support**
  → Make sure the Arabic language pack was installed with Tesseract (or manually add `ara.traineddata` to the `tessdata` folder), then set `OCR_LANGUAGES=eng+ara`.
