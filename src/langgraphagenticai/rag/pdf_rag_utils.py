import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

INDEX_ROOT = os.path.join(os.getcwd(), "pdf_indexes")
os.makedirs(INDEX_ROOT, exist_ok=True)


_embeddings_instance = None

def get_embeddings():
    """Uses HuggingFace's hosted Inference Endpoint (current, non-deprecated API)
    instead of a local model, so no heavy torch/transformers download is needed."""
    global _embeddings_instance
    if _embeddings_instance is None:
        from langchain_huggingface import HuggingFaceEndpointEmbeddings
        _embeddings_instance = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        )
    return _embeddings_instance


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def chunk_text(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    return splitter.split_text(text)


def build_index(file_path: str, conversation_id: int) -> str:
    """
    Extract -> chunk -> embed -> save FAISS index for this conversation.
    Returns the path the index was saved to.
    """
    from langchain_community.vectorstores import FAISS

    text = extract_text_from_pdf(file_path)
    if not text.strip():
        raise ValueError("No extractable text found in this PDF (it may be scanned/image-only).")

    chunks = chunk_text(text)
    embeddings = get_embeddings()

    vectorstore = FAISS.from_texts(chunks, embeddings)

    index_path = os.path.join(INDEX_ROOT, f"convo_{conversation_id}")
    vectorstore.save_local(index_path)
    return index_path


def load_index(conversation_id: int):
    from langchain_community.vectorstores import FAISS

    index_path = os.path.join(INDEX_ROOT, f"convo_{conversation_id}")
    if not os.path.exists(index_path):
        return None
    embeddings = get_embeddings()
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


def retrieve_chunks(conversation_id: int, query: str, k: int = 4):
    vectorstore = load_index(conversation_id)
    if vectorstore is None:
        return []
    results = vectorstore.similarity_search(query, k=k)
    return [doc.page_content for doc in results]

def build_index_from_text(text: str, course_id: str) -> str:
    """
    Chunk -> embed -> save FAISS index for a course (text-based, not PDF).
    """
    from langchain_community.vectorstores import FAISS

    if not text.strip():
        raise ValueError("No content provided to index for this course.")

    chunks = chunk_text(text)
    embeddings = get_embeddings()

    vectorstore = FAISS.from_texts(chunks, embeddings)

    index_path = os.path.join(INDEX_ROOT, f"convo_{course_id}")
    vectorstore.save_local(index_path)
    return index_path