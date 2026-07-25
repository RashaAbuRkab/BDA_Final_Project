# BDA Final Project: RAG PDF Teaching Demo

A Retrieval-Augmented Generation (RAG) project for exploring how grounding an LLM in a document, using both real **OCR** and **vision-LLM** image captioning,  changes the quality and reliability of its answers, compared to asking the same model without retrieval.

The system lets you upload a PDF, index its text **and** its images/scanned pages, then ask questions and compare:
- **Without RAG**:  the model answering from general knowledge alone
- **With RAG**:  the model answers only from what was actually retrieved from the document

---

## Repository Structure

This repo contains two parallel implementations, kept as separate folders so each extraction approach can be run, tested, and demoed independently:

| Folder | What it uses for images/scanned pages |
|---|---|
| [`BDA_Final_Project-OCR`](./BDA_Final_Project-OCR) | Real OCR via Tesseract (`pytesseract`), no LLM calls for image text extraction |
| [`BDA_Final_Project-visionLLM`](./BDA_Final_Project-visionLLM) | Vision-LLM captioning, a vision-capable chat model transcribes each image |

Both folders share the same overall architecture (FastAPI + LangChain + FAISS backend, Streamlit frontend) and the same core RAG flow, the only difference is *how* embedded images and scanned pages are turned into searchable text. Keeping them separate makes it easy to run each one on its own and compare results side-by-side.

See each folder's own README for full setup instructions, configuration, and API details specific to that approach.

---

## Quick Start

Each folder is a self-contained project, pick one (or run both, in separate terminals on separate ports) and follow its own README:

```
cd BDA_Final_Project-OCR
# see BDA_Final_Project-OCR/README.md for setup
```

```
cd BDA_Final_Project-visionLLM
# see BDA_Final_Project-visionLLM/README.md for setup
```

---

## Core Idea

The LLM does **not** read the PDF directly. Instead:

1. The document's text is chunked and embedded.
2. Its images and scanned pages are turned into searchable text, either by OCR or by a vision-LLM, depending on which folder you run.
3. FAISS retrieves the most semantically relevant pieces, text or image-derived, for a given question.
4. The LLM generates its answer using only that retrieved context.

Comparing the OCR and vision-LLM folders side-by-side demonstrates how the *method* used to extract text from non-text content affects what gets retrieved, and ultimately, the quality of the grounded answer.

<table>
  <tr>
    <th>Method</th>
    <th>Input File</th>
    <th>Output Image</th>
    <th>Extracted Data</th>
  </tr>

  <tr>
    <td><b>Vision LLM</b></td>
    <td rowspan="2" align="center">
      <img src="/images/Company Performance Report.png" >
    </td>
    <td align="center">
      <img src="/images/llm_results.png">
    </td>
    <td align="center">
      <img src="/images/llm_extract.png">
    </td>
  </tr>

  <tr>
    <td><b>OCR</b></td>
    <td align="center">
      <img src="/images/ocr_results.jpeg">
    </td>
    <td align="center">
      <img src="/images/ocr_extract.jpeg">
    </td>
  </tr>
</table>
