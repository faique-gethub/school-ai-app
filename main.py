IMAGE_KEYWORDS = [
    'generate image', 'draw', 'create image', 'make image',
    'image of', 'picture of', 'show image', 'banao image', 'tasveer'
]

@app.post("/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    count = get_message_count_today(req.student_email)
    if count >= DAILY_LIMIT:
        raise HTTPException(status_code=429,
            detail="Daily limit reached.")

    # Image request check karo seedha yahan
    lower_q = req.question.lower()
    is_image = any(k in lower_q for k in IMAGE_KEYWORDS)

    if is_image and not req.file_base64:
        encoded = urllib.parse.quote(req.question)
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=512&height=512&nologo=true"
        )
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
