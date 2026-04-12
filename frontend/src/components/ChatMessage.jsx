import Markdown from 'react-markdown';
import useAutoScroll from '../hooks/useAutoScroll';
import userIcon from '../asset/images/user.png'
import errorIcon from '../asset/images/error.png'

function ChatMessages({messages, isLoading}){
    const scrollContentRef = useAutoScroll(isLoading);
    return (
        <div ref={scrollContentRef} className='grow space-y-4'>
            {
                messages.map(({role,content,loading,error,sources},idx) => (
                    <div key={idx} className={`flex items-start gap-4 py-4 px-3 rounded-xl ${role === 'user' ? 'bg-primary-blue/10' : ''}`}>
                        {role === 'user' && (
                            <img 
                            className='h-[26px] w-[26px] shrink-0'
                            src ={userIcon} 
                            alt='user icon'/>
                        )}
                        <div>
                            <div className='markdown-container'>
                                {role === 'assistant' ? (
                                    loading && !content ? (
                                        <div className="text-gray-500">Thinking...</div>
                                    ) : (
                                        <Markdown>{content}</Markdown>
                                    )
                                ) : (
                                    <div className='whitespace-pre-line'>{content}</div>
                                )}
                            </div>
                            {role === 'assistant' && sources && sources.length > 0 && (
                                <div className="mt-3 space-y-1 text-sm">
                                    <p className="font-semibold text-gray-500">Sources:</p>
                                    {sources.map((s, i) => (
                                        <a
                                            key={i}
                                            href={s.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="block text-blue-500 underline break-all"
                                        >
                                            {s.url}
                                        </a>
                                    ))}
                                </div>
                            )}
                            {error && (
                                <div className={`flex items-center gap-1 text-sm text-error-red ${content && 'mt-2'}`}>
                                    <img className='h-5 w-5' src={errorIcon} alt='error' />
                                    <span>Error generating the response</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
        </div>
    );
}

export default ChatMessages;