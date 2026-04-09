const BASE_URL = 'http://localhost:8000';

function startChatStream(chatId, message, onMessage, onError, onComplete) {
    const url = `${BASE_URL}/chats/${chatId}?message=${encodeURIComponent(message)}`;
    const evtSource = new EventSource(url);

    evtSource.onopen = () => {
        console.log('SSE connection opened');
    };

    evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.event === "end") {
            evtSource.close();
            if (onComplete) onComplete();
            return;
        }

        onMessage(data);
    };

    evtSource.onerror = (err) => {
        console.log('SSE closed');

        if (evtSource.readyState === EventSource.CLOSED) {
            if (onComplete) onComplete();
            return;
        }

        console.error('Real SSE error', err);
        evtSource.close();
        if (onError) onError(err);
    };

    return evtSource;
}

// createChat stays the same
async function createChat() {
    const res = await fetch(`${BASE_URL}/chats`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    });
    const data = await res.json();
    if (!res.ok) {
        return Promise.reject({status: res.status, data});
    }
    return data;
}

export default { createChat, startChatStream };