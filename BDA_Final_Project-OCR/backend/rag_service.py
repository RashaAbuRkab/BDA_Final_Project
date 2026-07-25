import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import base64
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from backend.config import IMAGES_DIR  ## Add IMAGES_DIR to the existing import list

from backend.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    LLM_MODEL,
    TEMPERATURE,
    TOP_K,
    OPENAI_BASE_URL,
    TESSERACT_CMD,
    OCR_LANGUAGES,
)

load_dotenv()
github_token = os.getenv("GITHUB_TOKEN")
# Point pytesseract at a specific tesseract binary if configured (needed on
# Windows when tesseract.exe isn't on PATH).
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

vector_store = None


def load_pdf(file_path: str):
    loader = PyPDFLoader(file_path)
    return loader.load()


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def extract_images_from_pdf(file_path: str) -> list:
    doc_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(IMAGES_DIR, doc_name)
    os.makedirs(out_dir, exist_ok=True)

    pdf = fitz.open(file_path)
    extracted = []
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            # Ignore very small images (icons/ornaments) to save API calls
            if len(image_bytes) < 5000:
                continue

            filename = f"page{page_index+1}_img{img_index+1}.{ext}"
            path = os.path.join(out_dir, filename)
            with open(path, "wb") as f:
                f.write(image_bytes)
            extracted.append({"path": path, "page": page_index, "ext": ext})
    pdf.close()
    return extracted


def caption_image(image_path: str, ext: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    vision_llm = ChatOpenAI(model=LLM_MODEL, temperature=0, base_url=OPENAI_BASE_URL, api_key=github_token)

    message = HumanMessage(content=[
        {
            "type": "text",
            "text": (
                "Extract and transcribe ALL readable text, numbers, and table data from this image. "
                "If it contains a table, reproduce it as rows with clear labels and values. "
                "If it is a scanned document page, transcribe the full text content. "
                "Be exhaustive and precise — this will be used as the only source to answer questions."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
    ])
    response = vision_llm.invoke([message])
    return response.content


def ocr_image(image_path: str) -> str:
    """
    Run real OCR (Tesseract, via pytesseract) on an image or rasterized
    scanned page and return the raw extracted text.
    """
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES)
        return text.strip()
    except Exception as e:
        return f"(OCR failed: {e})"


def build_vector_store(chunks):
    global vector_store
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL, api_key=github_token)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(FAISS_INDEX_PATH)
    return vector_store


def ingest_pdf(file_path: str, extraction_method: str = "ocr") -> Dict[str, Any]:
    """
    extraction_method controls how embedded images / scanned pages are
    turned into searchable text:
      - "ocr"    -> real Tesseract OCR only (no vision LLM calls at all) [default]
      - "vision" -> vision-LLM captioning only (no OCR)
      - "both"   -> run both and store both
    """
    extraction_method = extraction_method.lower()
    if extraction_method not in ("ocr", "vision", "both"):
        raise ValueError('extraction_method must be one of: "ocr", "vision", "both"')

    documents = load_pdf(file_path)
    chunks = split_documents(documents)
    for c in chunks:
        c.metadata["type"] = "text"

    images = extract_images_from_pdf(file_path)
    scanned_pages = extract_scanned_pages(file_path)
    all_images = images + scanned_pages

    image_docs = []
    for img in all_images:
        ocr_text = None
        caption = None

        if extraction_method in ("ocr", "both"):
            ocr_text = ocr_image(img["path"])

        if extraction_method in ("vision", "both"):
            try:
                caption = caption_image(img["path"], img["ext"])
            except Exception as e:
                # Log the full error server-side, but don't dump it into the
                # searchable RAG content — a raw API traceback in a chunk is
                # noise for retrieval and ugly to show on screen.
                print(f"[vision captioning failed] page {img['page'] + 1}: {e}")
                caption = "(vision transcription unavailable for this image)"

        content_parts = [f"[Image/Scanned content - Page {img['page'] + 1}] (method: {extraction_method})"]
        if ocr_text is not None:
            if ocr_text and not ocr_text.startswith("(OCR failed"):
                content_parts.append(f"OCR Text:\n{ocr_text}")
            else:
                content_parts.append(f"OCR Text: (none detected — {ocr_text})" if ocr_text else "OCR Text: (none detected)")
        if caption is not None:
            content_parts.append(f"Vision Model Transcription:\n{caption}")

        image_docs.append(Document(
            page_content="\n\n".join(content_parts),
            metadata={
                "source": file_path,
                "page": img["page"],
                "type": "image",
                "image_path": img["path"],
                "ocr_text": ocr_text,
                "extraction_method": extraction_method,
            },
        ))

    all_chunks = chunks + image_docs
    build_vector_store(all_chunks)

    return {
        "pages": len(documents),
        "chunks": len(chunks),
        "images": len(image_docs),
        "extraction_method": extraction_method,
        "message": f"PDF indexed successfully (text + images + scanned pages, extraction_method={extraction_method})",
    }

def extract_scanned_pages(file_path: str, text_threshold: int = 30) -> list:
    """
    """
    doc_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = os.path.join(IMAGES_DIR, doc_name)
    os.makedirs(out_dir, exist_ok=True)

    pdf = fitz.open(file_path)
    scanned_pages = []
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        text = page.get_text().strip()

        if len(text) < text_threshold:
            pix = page.get_pixmap(dpi=200)
            filename = f"page{page_index+1}_fullpage.png"
            path = os.path.join(out_dir, filename)
            pix.save(path)
            scanned_pages.append({"path": path, "page": page_index, "ext": "png"})

    pdf.close()
    return scanned_pages

def get_retriever():
    global vector_store
    if vector_store is None:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL, api_key=github_token)
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )
    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": TOP_K,
            "score_threshold": 0.1,
        },
    )


def build_rag_prompt(question: str, retrieved_docs):
    context = "\n\n".join(
        [
            f"Source: {doc.metadata.get('source')} | Page: {doc.metadata.get('page')}\n{doc.page_content}"
            for doc in retrieved_docs
        ]
    )
    return f"""You are a document-grounded assistant.
Answer the question using only the context below.
If the answer is not available in the context, say:
"I don't know based on the provided PDF."

Context:
{context}

Question:
{question}

Answer:"""


def ask_without_rag(question: str) -> str:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=TEMPERATURE, base_url=OPENAI_BASE_URL, api_key=github_token)
    response = llm.invoke(question)
    return response.content


def ask_with_rag(question: str) -> Dict[str, Any]:
    global vector_store
    if vector_store is None:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL, api_key=github_token)
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    docs_and_scores = vector_store.similarity_search_with_score(question, k=TOP_K)
    retrieved_docs = [doc for doc, score in docs_and_scores]
    prompt = build_rag_prompt(question, retrieved_docs)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=TEMPERATURE, base_url=OPENAI_BASE_URL, api_key=github_token)
    response = llm.invoke(prompt)

    chunks = []
    for doc, score in docs_and_scores:
        source = os.path.basename(doc.metadata.get("source", ""))
        page = doc.metadata.get("page", 0) + 1
        chunks.append(
            {
                "content": doc.page_content,
                "source": source,
                "page": page,
                "score": float(score),
                "type": doc.metadata.get("type", "text"),
                "image_path": doc.metadata.get("image_path"),
                "ocr_text": doc.metadata.get("ocr_text"),
                "extraction_method": doc.metadata.get("extraction_method"),
            }
        )

    return {
        "answer": response.content,
        "chunks": chunks,
    }