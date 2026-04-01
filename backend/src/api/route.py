from uuid import uuid4
from time import time
from fastapi import APIRouter,Depends, HTTPException
from pydantic import BaseModel
from src.data.chat_db import get_redis, create_chat, chat_exists,add_chat_messages,get_chat_messages
from src.agent.chat import rag_recall,generate_answer
from src.config.prompt import PROMPT
router = APIRouter()

class ChatIn(BaseModel):
    message: str

async def get_rdb():
    rdb = get_redis()
    try:
        yield rdb
    finally:
        await rdb.close()


@router.post('/chats')
async def create_new_chat(rdb = Depends(get_rdb)):
    chat_id = str(uuid4())[:8]
    created = int(time())
    await create_chat(rdb, chat_id, created)
    return {'id': chat_id}

@router.post('/chats/{chat_id}')
async def chat(chat_id: str, chat_in: ChatIn, rdb=Depends(get_rdb)):

    # 1️⃣ Check chat exists
    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail=f'Chat {chat_id} does not exist')

    # 2️⃣ Save user message
    user_msg = {"role": "user", "content": chat_in.message}
    await add_chat_messages(rdb, chat_id, [user_msg])

    # 3️⃣ Get recent history
    history = await get_chat_messages(rdb, chat_id, last_n=5)

    # 4️⃣ Retrieve knowledge (RAG)
    top_docs = rag_recall(chat_in.message)

    # 🔥 5️⃣ Confidence check (VERY IMPORTANT)
    if not top_docs or top_docs[0][1] < 0.4:
        response_text = "I can't provide an answer for this question."
    else:
        # 6️⃣ Build context
        rag_context = "\n\n".join([doc for doc, _ in top_docs])

        # 7️⃣ Build chat history string
        history_text = ""
        for msg in history:
            history_text += f"{msg['role']}: {msg['content']}\n"

        # 8️⃣ Final prompt
        final_prompt = f"""
{PROMPT}

Chat History:
{history_text}

Context:
{rag_context}

User Question:
{chat_in.message}

Answer:
"""

        # 9️⃣ Generate
        response_text = generate_answer(final_prompt)

    # 🔟 Save assistant response
    bot_message = {"role": "assistant", "content": response_text}
    await add_chat_messages(rdb, chat_id, [bot_message])

    # ✅ Return response + sources
    return {
        "response": response_text,
        "chat_id": chat_id,
        "sources": [doc for doc, _ in top_docs] if top_docs else []
    }
