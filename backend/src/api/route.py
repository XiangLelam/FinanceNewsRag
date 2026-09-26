from uuid import uuid4
from time import time
from fastapi import APIRouter,Depends, HTTPException, Query
from src.data.chat_db import get_redis, create_chat, chat_exists,add_chat_messages,get_chat_messages
from src.agent.rag import rag_recall, is_confident, extract_keywords, should_update_kb, mark_kb_updated
from src.agent.agents import typo_corrector_agent, rewrite_query_agent, generate_answer_agent
from src.config.prompt import (
    PROMPT,
    LOW_CONFIDENCE_PROMPT,
    FETCH_FAILED_MESSAGE,
    NO_MATCH_REASON,
    LOW_RELEVANCE_REASON
)
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
from urllib.parse import urlparse
import asyncio
import json
from src.data.knowledge_process import KnowledgeProcessing
import src.config.constant as cons

router = APIRouter()


def format_context(top_docs):
    parts = []
    for i, (doc, _) in enumerate(top_docs, 1):
        if not isinstance(doc, dict):
            parts.append(f"[{i}]\n{doc}")
            continue

        source = urlparse(doc.get("url") or "").netloc.replace("www.", "") or "unknown source"
        date = doc.get("date")
        date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else (date or "unknown date")

        parts.append(f"[{i}] {doc.get('title') or 'Untitled'} ({source}, published {date_str})\n{doc['text']}")

    return "\n\n".join(parts)

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

    history = await get_chat_messages(rdb, chat_id, last_n=cons.CHAT_HISTORY_SIZE)
    history = [m for m in history if m.get("content") != FETCH_FAILED_MESSAGE]
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    user_msg = {"role": "user", "content": message}
    await add_chat_messages(rdb, chat_id, [user_msg])

    print(f"\n{'='*60}")
    print(f"User Query: '{message}'")
    
    corrected_query = typo_corrector_agent(message)
    if corrected_query != message:
        print(f"LLM Typo Correction: '{message}' → '{corrected_query}'")
    else:
        print(f"No typos detected in query")
    
    normalised_query = rewrite_query_agent(corrected_query, history_text)
    print(f"Normalized: '{normalised_query}'")

    gdelt_keywords = extract_keywords(normalised_query, correct_typos=False)
    print(f"Keywords: '{gdelt_keywords}'")
    
    kb_needs_update = should_update_kb(gdelt_keywords)
    
    print(f"\nKB Persistence Check: kb_needs_update={kb_needs_update}")
    print(f"Fetching articles using keywords: '{gdelt_keywords}'")
    if kb_needs_update:
        print(f"Updating KB with new keywords...")
        kp = KnowledgeProcessing(gdelt_keywords)
        kb_updated = kp.update_knowledge()
        if kb_updated:
            mark_kb_updated(gdelt_keywords)
            print(f"KB updated successfully")
        else:
            print(f"KB update failed")
    else:
        kb_updated = False
        print(f"Reusing existing KB (keywords unchanged)")
    
    fetch_failed = kb_needs_update and not kb_updated

    print(f"\nPerforming RAG retrieval...")
    if fetch_failed:
        print("News fetch failed - skipping retrieval")
        top_docs = []
    else:
        try:
            top_docs = rag_recall(
                query=corrected_query,
                normalized_query=normalised_query,
                keywords=gdelt_keywords,
                skip_kb_update=True
            )
            print(f"Retrieved {len(top_docs)} documents")
            if len(top_docs) > 0:
                print(f"Top scores: {[f'{score:.4f}' for _, score in top_docs]}")
        except Exception as e:
            print(f"RAG recall error: {e}")
            import traceback
            traceback.print_exc()
            top_docs = []
    
    use_context = is_confident(top_docs)

    today = datetime.now().strftime("%A, %d %B %Y")
    history_for_prompt = history_text or "(no previous messages)"

    if use_context:
        final_prompt = PROMPT.format(
            today=today,
            history=history_for_prompt,
            context=format_context(top_docs),
            question=corrected_query
        )
        print(f"Using {len(top_docs)} sources with high confidence")
    else:
        reason = LOW_RELEVANCE_REASON if top_docs else NO_MATCH_REASON
        print(f"No confident context ({reason}) - using LLM without context")
        final_prompt = LOW_CONFIDENCE_PROMPT.format(
            today=today,
            reason=reason,
            history=history_for_prompt,
            question=corrected_query
        )

    async def event_generator():
        try:
            if fetch_failed:
                full_response = FETCH_FAILED_MESSAGE
            else:
                full_response = generate_answer_agent(final_prompt)

            for i in range(0, len(full_response), cons.STREAMING_CHUNK_SIZE):
                chunk = full_response[i:i+cons.STREAMING_CHUNK_SIZE]

                yield json.dumps({
                    "role": "assistant",
                    "content": chunk,
                    "error": False
                })

                await asyncio.sleep(cons.STREAMING_DELAY)

            try:
                await add_chat_messages(rdb, chat_id, [
                    {"role": "assistant", "content": full_response}
                ])
            except Exception as e:
                print("Redis error:", e)

            low_confidence = not use_context

            if use_context:
                sources_dict = {}
                for doc, score in top_docs:
                    url = doc.get("url", "N/A")
                    if url not in sources_dict or sources_dict[url]["score"] < round(score, 3):
                        sources_dict[url] = {
                            "url": url,
                            "score": round(score, 3),
                            "title": doc.get("title", "N/A")
                        }
                
                sources = list(sources_dict.values())
                print(f"Returning {len(sources)} unique sources (deduplicated by URL)")
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
            print("STREAM ERROR:", e)

            yield json.dumps({
                "role": "assistant",
                "content": "Internal error occurred",
                "error": True
            })

    return EventSourceResponse(event_generator(), media_type="text/event-stream")