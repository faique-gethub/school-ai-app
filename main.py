from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from ai_engine import get_answer
from database import save_chat, get_chat_history, check_school_active
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    question: str
    school_id: str
    student_email: str

@app.get("/")
def home():
    return {"message": "School AI App is running!"}

@app.post("/ask")
def ask_question(data: Question):
    answer = get_answer(data.question, data.school_id)
    save_chat(data.student_email, data.school_id, data.question, answer)
    return {
        "question": data.question,
        "school_id": data.school_id,
        "answer": answer
    }

@app.get("/history/{student_email}")
def chat_history(student_email: str):
    history = get_chat_history(student_email)
    return {"history": history}
