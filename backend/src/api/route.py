from uuid import uuid4
from time import time
from fastapi import APIRouter,Depends, HTTPException, Query
from pydantic import BaseModel
from src.data.chat_db import get_redis, create_chat, chat_exists,add_chat_messages,get_chat_messages
from src.agent.chat import rag_recall,generate_answer,build_prompt
from src.config.prompt import PROMPT
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

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



@router.get('/chats/{chat_id}')
async def stream_chat(chat_id: str, message: str = Query(...), rdb=Depends(get_rdb)):

    if not await chat_exists(rdb, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = {"role": "user", "content": message}
    await add_chat_messages(rdb, chat_id, [user_msg])

    history = await get_chat_messages(rdb, chat_id, last_n=5)

    top_docs = rag_recall(message)

    # ✅ FIXED
    context = "\n\n".join([doc for doc, _ in top_docs])

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    final_prompt = f"""
{PROMPT}

Chat History:
{history_text}

Context:
{context}

User Question:
{message}

Answer:
"""

    async def event_generator():
        try:
            full_response = generate_answer(final_prompt, max_tokens=100)

            for i in range(0, len(full_response), 50):
                chunk = full_response[i:i+50]

                yield json.dumps({
                    "role": "assistant",
                    "content": chunk,
                    "error": False
                })

                await asyncio.sleep(0.05)

            # ✅ Safe Redis save
            try:
                await add_chat_messages(rdb, chat_id, [
                    {"role": "assistant", "content": full_response}
                ])
            except Exception as e:
                print("⚠️ Redis error:", e)

            # ✅ End signal (important for frontend)
            yield json.dumps({"event": "end"})

        except Exception as e:
            print("❌ STREAM ERROR:", e)

            yield json.dumps({
                "role": "assistant",
                "content": "Internal error occurred",
                "error": True
            })

    return EventSourceResponse(event_generator(), media_type="text/event-stream")