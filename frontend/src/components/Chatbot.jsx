import { useState } from 'react';
import { useImmer } from 'use-immer';
import api from '../api';
import ChatMessages from './ChatMessage';
import ChatInput from './ChatInput';

function Chatbot() {
    const [chatId, setChatId] = useState(null);
    const [messages, setMessages] = useImmer([]);
    const [newMessage, setNewMessage] = useState('')
    const isLoading = messages.length && messages[messages.length -1].loading;
    async function submitNewMessage() {
        const trimmedMessage = newMessage.trim();
        if (!trimmedMessage || isLoading) return;

        setMessages(draft => [
            ...draft,
            { role: 'user', content: trimmedMessage },
            { role: 'assistant', content: '', loading: true }
        ]);
        setNewMessage('');
        await new Promise(requestAnimationFrame);
        let chatIdOrNew = chatId;

        try {
            if (!chatId) {
                const { id } = await api.createChat();
                setChatId(id);
                chatIdOrNew = id;
            }

            const sse = api.startChatStream(
                chatIdOrNew,
                trimmedMessage,
                (data) => {
                    setMessages(draft => {
                        draft[draft.length - 1].content += data.content;
                    });
                },
                (err) => {
                    setMessages(draft => {
                        draft[draft.length - 1].loading = false;
                        draft[draft.length - 1].error = true;
                    });
                },
                (sources) => {
                    setMessages(draft => {
                        draft[draft.length - 1].loading = false;
                        draft[draft.length - 1].sources = sources;
                    });
                }
            );

        } catch (err) {
            console.log(err);
            setMessages(draft => {
                draft[draft.length - 1].loading = false;
                draft[draft.length - 1].error = true;
            });
        }
    }
    
    return(
        <div className='relative grow flex flex-col gap-6 pt-6'>
            {messages.length === 0 && (
                <div className='mt-3 font-urbanist text-primary-blue text-xl font-light space-y-2'>
                    <p>Welcome</p>
                    <p>I am finance chatbot</p>
                    <p>Ask me anything about latest finance news</p>
                </div>
            )}
            <ChatMessages
                messages={messages}
                isLoading = {isLoading}
            />
            <ChatInput
                newMessage = {newMessage}
                isLoading = {isLoading}
                setNewMessage = {setNewMessage}
                submitNewMessage={submitNewMessage}
            />
        </div>
        
    )
}



export default Chatbot;


