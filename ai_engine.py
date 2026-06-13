import os
import base64
import tempfile
from dotenv import load_dotenv
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
embeddings = FakeEmbeddings(size=384)


def load_books():
    books_path = "books"
    all_docs = []
    if not os.path.exists(books_path):
        os.makedirs(books_path)
        return []
    for root, dirs, files in os.walk(books_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                try:
                    pdf_path = os.path.join(root, file)
                    loader = PyPDFLoader(pdf_path)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["book_name"] = file
                    all_docs.extend(docs)
                    print(f"Loaded: {file}")
                except Exception as e:
                    print(f"Error loading {file}: {e}")
    return all_docs


def get_pdf_context(question):
    docs = load_books()
    if not docs:
        return None
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    db = Chroma.from_documents(chunks, embeddings)
    results = db.similarity_search(question, k=5)
    if not results:
        return None
    return "\n\n".join([r.page_content for r in results])


def build_messages(system_prompt, question, chat_history=None):
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for item in chat_history[-6:]:
            messages.append({"role": "user", "content": item["question"]})
            messages.append({"role": "assistant", "content": item["answer"]})
    messages.append({"role": "user", "content": question})
    return messages


def general_answer(question, chat_history=None):
    system = (
        "You are Novaaq.E, an AI school assistant. "
        "Give accurate, clear answers with markdown formatting. "
        "Explain like a teacher for study questions. "
        "Be helpful, concise, and complete."
    )
    messages = build_messages(system, question, chat_history)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.5,
        max_tokens=1500
    )
    return response.choices[0].message.content


def pdf_answer(question, context, chat_history=None):
    system = (
        f"You are Novaaq.E, an AI school assistant.\n\n"
        f"Answer using this PDF content:\n\n{context}\n\n"
        f"If not found in PDF, say: "
        f"'This information was not found in the uploaded books.'\n"
        f"Use markdown formatting."
    )
    messages = build_messages(system, question, chat_history)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=1500
    )
    return response.choices[0].message.content


def answer_from_attached_pdf(question, file_base64, file_name, chat_history=None):
    try:
        # Decode and save to temp file
        file_bytes = base64.b64decode(file_base64)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf"
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        os.unlink(tmp_path)

        if not docs:
            return general_answer(question, chat_history)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700, chunk_overlap=100
        )
        chunks = splitter.split_documents(docs)
        db = Chroma.from_documents(chunks, embeddings)
        results = db.similarity_search(question, k=5)
        context = "\n\n".join([r.page_content for r in results])

        system = (
            f"You are Novaaq.E. The user attached a PDF: '{file_name}'.\n\n"
            f"Answer using this content:\n\n{context}\n\n"
            f"Use markdown formatting."
        )
        messages = build_messages(system, question, chat_history)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error processing attached PDF: {e}")
        return general_answer(question, chat_history)


def answer_from_image(question, file_base64, file_name, chat_history=None):
    # Groq vision model for image analysis
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{file_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": question
                    }
                ]
            }
        ]
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Image analysis error: {e}")
        return f"Could not analyze image: {str(e)}"


def get_answer_with_file(
    question, file_base64, file_type, file_name, chat_history=None
):
    if file_type == "pdf":
        return answer_from_attached_pdf(
            question, file_base64, file_name, chat_history
        )
    elif file_type == "image":
        return answer_from_image(
            question, file_base64, file_name, chat_history
        )
    return general_answer(question, chat_history)


def get_answer(question, chat_history=None):
    try:
        context = get_pdf_context(question)
        if context:
            print("Using PDF context")
            return pdf_answer(question, context, chat_history)
        print("Using general AI")
        return general_answer(question, chat_history)
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {str(e)}"
