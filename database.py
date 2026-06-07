import os
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

def save_chat(student_email, school_id, question, answer):
    try:
        supabase.table("chat_history").insert({
            "student_email": student_email,
            "school_id": school_id,
            "question": question,
            "answer": answer
        }).execute()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_chat_history(student_email):
    try:
        result = supabase.table("chat_history").select("*").eq(
            "student_email", student_email
        ).execute()
        return result.data
    except Exception as e:
        return []

def check_school_active(school_id):
    try:
        result = supabase.table("schools").select("*").eq(
            "school_id", school_id
        ).eq("is_active", True).execute()
        return len(result.data) > 0
    except Exception as e:
        return False
