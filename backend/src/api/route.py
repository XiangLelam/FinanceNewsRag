from uuid import uuid4
from time import time
from fastapi import APIRouter,Depends, HTTPException, Query
from src.data.chat_db import get_redis, create_chat, chat_exists,add_chat_messages,get_chat_messages
from src.agent.chat import rag_recall,generate_answer, is_confident
from src.config.prompt import PROMPT
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from src.data.knowledge_process import KnowledgeProcessing

router = APIRouter()

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
    kp = KnowledgeProcessing(message)
    kp.update_knowledge()
    top_docs = rag_recall(message)

    use_context = is_confident(top_docs)

    if use_context:
        context_parts = []
        for doc, _ in top_docs:
            if isinstance(doc, dict):
                context_parts.append(doc["text"])
            else:
                context_parts.append(str(doc))

        context = "\n\n".join(context_parts)
    else:
        print("⚠️ Low confidence → fallback to LLM (no context)")
        context = ""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    if context:
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
    else:
        final_prompt = f"""
            {PROMPT}

            Chat History:
            {history_text}

            User Question:
            {message}

            Answer:
        """

    async def event_generator():
        try:
            full_response = generate_answer(final_prompt)

            # Stream chunks
            for i in range(0, len(full_response), 50):
                chunk = full_response[i:i+50]

                yield json.dumps({
                    "role": "assistant",
                    "content": chunk,
                    "error": False
                })

                await asyncio.sleep(0.05)

            try:
                await add_chat_messages(rdb, chat_id, [
                    {"role": "assistant", "content": full_response}
                ])
            except Exception as e:
                print("⚠️ Redis error:", e)

            low_confidence = not use_context

            if use_context:
                sources = [
                    {
                        "url": doc.get("url", "N/A"),
                        "score": round(score, 3)
                    }
                    for doc, score in top_docs
                ]
            else:
                sources = []

            low_confidence = not use_context

            yield {
                "event": "end",
                "data": json.dumps({
                    "sources": sources,
                    "low_confidence": low_confidence
                })
            }

        except Exception as e:
            print("❌ STREAM ERROR:", e)

            yield json.dumps({
                "role": "assistant",
                "content": "Internal error occurred",
                "error": True
            })

    return EventSourceResponse(event_generator(), media_type="text/event-stream")