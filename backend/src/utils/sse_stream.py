import asyncio
from sse_starlette import ServerSentEvent

class SSEStream:
    """Helper for async Server-Sent Events streaming.

    This class exposes an async iterator interface so it can be used with
    frameworks that support streaming response bodies using async iteration.
    """

    def __init__(self):
        # Internal queue holds outgoing SSE payloads.
        self._queue = asyncio.Queue()
        # Unique sentinel object used to signal the end of the stream.
        self._stream_end = object()

    def __aiter__(self):
        # Return self to support async iteration: "async for event in stream".
        return self
    
    async def __anext__(self):
        # Wait for the next queued event.
        data = await self._queue.get()
        # If the sentinel is received, stop iteration cleanly.
        if data is self._stream_end:
            raise StopAsyncIteration
        # Wrap raw payload into a ServerSentEvent for SSE transport.
        return ServerSentEvent(data=data)
    
    async def send(self, data):
        """Queue a piece of data to be sent to the client."""
        await self._queue.put(data)

    async def close(self):
        """Signal that the SSE stream is complete."""
        await self._queue.put(self._stream_end)