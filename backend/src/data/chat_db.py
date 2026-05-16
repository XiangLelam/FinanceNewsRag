import os
from dotenv import load_dotenv
import json
from redis.asyncio import Redis
from redis.commands.search.field import NumericField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.json.path import Path
import src.config.constant as cons

load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-json')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

CHAT_IDX_PREFIX = cons.CHAT_IDX_PREFIX
CHAT_IDX_NAME = cons.CHAT_IDX_NAME

def get_redis():
    return Redis(host=REDIS_HOST,port=REDIS_PORT)

async def create_chat_index(rdb):
    try:
        schema = (
            NumericField('$.created', as_name = 'created' , sortable = True)
        )
        await rdb.ft(CHAT_IDX_NAME).create_index(
            fields =schema,
            definition = IndexDefinition(prefix=[CHAT_IDX_PREFIX], index_type = IndexType.JSON)
        )
        print(f"Chat index '{CHAT_IDX_NAME}' created successfully")
    except Exception as e:
        print(f"Error creating chat index '{CHAT_IDX_NAME}' : {e}")
async def create_chat(rdb, chat_id, created):
    chat = {'id':chat_id,'created': created,'messages' : []}
    await rdb.json().set(CHAT_IDX_PREFIX + chat_id , Path.root_path(), chat)
    return chat

async def add_chat_messages(rdb, chat_id, messages):
    await rdb.json().arrappend(CHAT_IDX_PREFIX + chat_id, '$.messages', *messages)

async def chat_exists(rdb, chat_id):
    return await rdb.exists(CHAT_IDX_PREFIX + chat_id)

async def get_chat_messages(rdb, chat_id, last_n=None):
    key = CHAT_IDX_PREFIX + chat_id
    if last_n is None:
        messages = await rdb.json().get(key, '$.messages[*]')
    else:
        messages = await rdb.json().get(key, f'$.messages[-{last_n}:]')
    return messages if messages else []
async def get_all_chats(rdb):
    q = Query('*').sort_by('created', asc=False)
    count = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0,0))
    res = await rdb.ft(CHAT_IDX_NAME).search(q.paging(0, count.total))
    return [json.loads(doc.json) for doc in res.docs]