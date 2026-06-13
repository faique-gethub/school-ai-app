import os
import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from ai_engine import get_answer, get_answer_with_file
from database import save_chat, get_chat_history, get_message_count_today
import google.generativeai as genai

load_dotenv()

app = FastAPI(title="Novaaq.E Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DAILY_LIMIT = 40

IMAGE_KEYWORDS = [
    'generate image', 'draw', 'create image', 'make image',
    'image of', 'picture of', 'show image', 'banao image', 'tasveer'
]

# Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class LoginRequest(BaseModel):
    email: str

class AskRequest(BaseModel):
    question: str
    student_email: str
    school_id: str = "default"
    file_base64: Optional[str] = None
    file_type: Optional[str] = None
    file_name: Optional[str] = None

class ImageRequest(BaseModel):
    prompt: str
    student_email: str

@app.get("/")
def root():
    return {"message": "Novaaq.E Backend Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    return {"success": True, "email": email, "school_id": "default"}

@app.post("/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    count = get_message_count_today(req.student_email)
    if count >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily limit reached.")

    lower_q = req.question.lower()
    is_image = any(k in lower_q for k in IMAGE_KEYWORDS)

    if is_image and not req.file_base64:
        # Use Gemini for image generation
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')
            response = model.generate_content(
                f"Generate an image: {req.prompt}",
                generation_config={"response_modalities": ["TEXT", "IMAGE"]}
            )
            
            # Extract image from response
            image_url = None
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_url = f"data:image/png;base64,{part.inline_data.data}"
                    break
            
            if not image_url:
                # Fallback to Pollinations
                encoded = urllib.parse.quote(req.question)
                image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
            
            save_chat(req.student_email, req.school_id, req.question, image_url)
            return {
                "success": True,
                "question": req.question,
                "answer": "__IMAGE__:" + image_url,
                "messages_used": count + 1,
                "messages_remaining": DAILY_LIMIT - count - 1
            }
        except Exception as e:
            # Fallback to Pollinations
            encoded = urllib.parse.quote(req.question)
            image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
            save_chat(req.student_email, req.school_id, req.question, image_url)
            return {
                "success": True,
                "question": req.question,
                "answer": "__IMAGE__:" + image_url,
                "messages_used": count + 1,
                "messages_remaining": DAILY_LIMIT - count - 1
            }

    history_raw = get_chat_history(req.student_email, limit=6)
    chat_history = list(reversed(history_raw))

    if req.file_base64 and req.file_type:
        answer = get_answer_with_file(
            question=req.question,
            file_base64=req.file_base64,
            file_type=req.file_type,
            file_name=req.file_name or "file",
            chat_history=chat_history
        )
    else:
        answer = get_answer(req.question, chat_history)

    save_chat(req.student_email, req.school_id, req.question, answer)

    return {
        "success": True,
        "question": req.question,
        "answer": answer,
        "messages_used": count + 1,
        "messages_remaining": DAILY_LIMIT - count - 1
    }

@app.post("/generate-image")
def generate_image(req: ImageRequest):
    count = get_message_count_today(req.student_email)
    if count >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily limit reached.")

    try:
        # Use Gemini for image generation
        model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')
        response = model.generate_content(
            f"Generate a detailed image: {req.prompt}",
            generation_config={"response_modalities": ["TEXT", "IMAGE"]}
        )
        
        # Extract image from response
        image_data = None
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                break
        
        if image_data:
            import base64
            image_url = f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
            save_chat(req.student_email, "default", f"[Image] {req.prompt}", image_url)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": req.prompt
            }
        else:
            # Fallback to Pollinations
            encoded_prompt = urllib.parse.quote(req.prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
            save_chat(req.student_email, "default", f"[Image] {req.prompt}", image_url)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": req.prompt
            }
    except Exception as e:
        # Fallback to Pollinations
        encoded_prompt = urllib.parse.quote(req.prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
        save_chat(req.student_email, "default", f"[Image] {req.prompt}", image_url)
        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt
        }

@app.get("/history/{student_email}")
def history(student_email: str):
    data = get_chat_history(student_email, limit=50)
    return {"success": True, "history": data}

@app.delete("/history/{student_email}")
def delete_history(student_email: str):
    try:
        from database import supabase
        supabase.table("chat_history").delete().eq(
            "student_email", student_email).execute()
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
