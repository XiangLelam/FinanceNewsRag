import Markdown from 'react-markdown';
import useAutoScroll from '@/hooks/useAutoScroll';
import Spinner from '@/components/Spinner';
import userIcon from '@/assests/images/user.svg'
import errorIcon from '@/assests/images/error.svg'

function ChatMessages({messages, isLoading}){
    const scrollContentRef = useAutoScroll(isLoading);
    return (
        <div ref={scrollContentRef}>
            {
                messages.map(({role,content,loading,error},idx) => (
                    <div key ={idx}>
                        {role == 'user' && (
                            <img src ={userIcon} alt='user icon'/>
                        )}
                        <div>
                            <div>
                                {(loading && !content) ? <Spinner />
                                    :(role === 'assistant')
                                    ? <Markdown>{content}</Markdown>
                                    :<div>{content}</div>
                                }
                            </div>
                            {error && (
                                <div>
                                    <img src = {errorIcon} alt='error icon' />
                                    <span>Error generating response</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
        </div>
    );
}

export default ChatMessages;