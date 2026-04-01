import useAutosize from '@hooks/useAutosize';
import sendIcon from '@/asset/images/send.png'
function ChatInput({newMessage, isLoading,setNewMessage, submitNewMessage}){
    const textareaRef = useAutosize(newMessage)
    function handleKeyDown(e){
        if(e.keyCode === 13 && !e.shiftKey && !isLoading){
            e.preventDefault();
            submitNewMessage();
        }
    }
    return (
        <div>
            <textarea 
                ref={textareaRef}
                row='l'
                value={newMessage}
                onChange={e => setNewMessage(e.target.value)}
                onKeyDown={handleKeyDown}
            />
            <button onClick={submitNewMessage}>
                <img src={sendIcon} alt='send'/>
            </button>
        </div>
    );
}
export default ChatInput;