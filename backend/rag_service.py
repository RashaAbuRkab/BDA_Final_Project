import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import base64
import fitz  # PyMuPDF
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
)

load_dotenv()

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

    vision_llm = ChatOpenAI(model=LLM_MODEL, temperature=0, base_url=OPENAI_BASE_URL)

    message = HumanMessage(content=[
        {
            "type": "text",
            "text": "Describe the content of this image accurately and briefly (2-3 sentences). "
                    "Mention any visible text, numbers, chart labels, or table headers. "
                    "This description will be used in a text-based search system.",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/{ext};base64,{b64}"},
        },
    ])
    response = vision_llm.invoke([message])
    return response.content

def build_vector_store(chunks):
    global vector_store
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(FAISS_INDEX_PATH)
    return vector_store


def ingest_pdf(file_path: str) -> Dict[str, Any]:
    documents = load_pdf(file_path)
    chunks = split_documents(documents)
    for c in chunks:
        c.metadata["type"] = "text"

    images = extract_images_from_pdf(file_path)
    image_docs = []
    for img in images:
        try:
            caption = caption_image(img["path"], img["ext"])
        except Exception as e:
            caption = f"Feild image: {e}"

        image_docs.append(Document(
            page_content=f"[Image - Page {img['page'] + 1}]: {caption}",
            metadata={
                "source": file_path,
                "page": img["page"],
                "type": "image",
                "image_path": img["path"],
            },
        ))

    all_chunks = chunks + image_docs
    build_vector_store(all_chunks)

    return {
        "pages": len(documents),
        "chunks": len(chunks),
        "images": len(image_docs),
        "message": "PDF indexed successfully (text + images)",
    }


def get_retriever():
    global vector_store
    if vector_store is None:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL)
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
    llm = ChatOpenAI(model=LLM_MODEL, temperature=TEMPERATURE, base_url=OPENAI_BASE_URL)
    response = llm.invoke(question)
    return response.content


def ask_with_rag(question: str) -> Dict[str, Any]:
    global vector_store
    if vector_store is None:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL)
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    docs_and_scores = vector_store.similarity_search_with_score(question, k=TOP_K)
    retrieved_docs = [doc for doc, score in docs_and_scores]
    prompt = build_rag_prompt(question, retrieved_docs)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=TEMPERATURE, base_url=OPENAI_BASE_URL)
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
            }
        )

    return {
        "answer": response.content,
        "chunks": chunks,
    }