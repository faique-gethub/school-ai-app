from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embeddings = FakeEmbeddings(size=384)

def load_books(school_id: str):
    books_path = f"books/{school_id}"
    all_docs = []
    if not os.path.exists(books_path):
        os.makedirs(books_path)
        return []
    for file in os.listdir(books_path):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(f"{books_path}/{file}")
            all_docs.extend(loader.load())
    return all_docs

def get_answer(question: str, school_id: str):
    docs = load_books(school_id)
    if not docs:
        return "No books uploaded for this school yet."
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    db = Chroma.from_documents(chunks, embeddings)
    results = db.similarity_search(question, k=3)
    context = "\n".join([r.page_content for r in results])
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a school AI assistant. Answer from this content:\n{context}\n\nIf answer is not in content, answer from your general knowledge."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
