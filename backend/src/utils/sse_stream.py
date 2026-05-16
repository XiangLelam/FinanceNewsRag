import asyncio
from sse_starlette import ServerSentEvent

class SSEStream:
    """Helper for async Server-Sent Events streaming.

    This class exposes an async iterator interface so it can be used with
    frameworks that support streaming response bodies using async iteration.
    """

    def __init__(self):
        self._queue = asyncio.Queue()
        self._stream_end = object()

    def __aiter__(self):
        return self
    
    async def __anext__(self):
        data = await self._queue.get()
        if data is self._stream_end:
            raise StopAsyncIteration
        return ServerSentEvent(data=data)
    
    async def send(self,data):
        await self._queue.put(data)

    async def close(self):
        await self._queue.put(self._stream_end)