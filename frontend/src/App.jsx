import Chatbot from '@/components/Chatbot';
import logo from '@/assests/images/logo.svg';

function App(){
    return (
        <div className='flex flex-col min-h-full w-full max-w-3xl mx-auto px4'>
            <header>
                <div className='flex flex-col h-full w-full gap-1 pt-4 pb-2'>
                    <a href= 'https://example.com'>
                        <img src={logo} className='w-32' alt='logo'/>
                    </a>
                    <h1 className='font-urbanist text-[1.65rem] font-semibold'>Finance News Chatbot</h1>
                </div>
            </header>
            <Chatbot/>
        </div>
    )
}

export default App;
