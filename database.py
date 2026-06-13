import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def save_chat(student_email: str, school_id: str, question: str, answer: str):
    try:
        supabase.table("chat_history").insert({
            "student_email": student_email,
            "school_id": school_id,
            "question": question,
            "answer": answer
        }).execute()
    except Exception as e:
        print(f"Error saving chat: {e}")


def get_chat_history(student_email: str, limit: int = 50):
    try:
        response = (
            supabase.table("chat_history")
            .select("*")
            .eq("student_email", student_email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


def get_message_count_today(student_email: str):
    from datetime import datetime, timezone
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = (
            supabase.table("chat_history")
            .select("id")
            .eq("student_email", student_email)
            .gte("created_at", f"{today}T00:00:00")
            .execute()
        )
        return len(response.data)
    except Exception as e:
        print(f"Error counting messages: {e}")
        return 0
