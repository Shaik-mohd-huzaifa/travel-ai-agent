import React, { RefObject, useState } from 'react';
import { Paperclip, Mic, Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  inputValue?: string;
  setInputValue?: React.Dispatch<React.SetStateAction<string>>;
  inputRef?: RefObject<HTMLInputElement>;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  inputValue = '', 
  setInputValue,
  inputRef
}) => {
  const [localMessage, setLocalMessage] = useState('');
  
  // Use external input value if provided
  const message = setInputValue ? inputValue : localMessage;
  const setMessage = setInputValue ? setInputValue : setLocalMessage;
  
  // Use the inputValue prop if passed from a parent component
  React.useEffect(() => {
    if (inputValue && setInputValue) {
      setInputValue(inputValue);
    }
  }, [inputValue, setInputValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <div className="chat-input-container p-4 border-t border-gray-200">
      <div className="flex flex-col items-center">
        <p className="text-xs text-gray-500 text-center mb-2">
          Travel AI may display inaccurate info, so please double check the response.
        </p>
        
        <form onSubmit={handleSubmit} className="relative w-[80%]">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask me anything about travel..."
            className="w-full px-6 py-4 pr-32 border border-gray-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-gray-800 rounded-xl font-inter"
            ref={inputRef}
          />
          
          <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
            <button 
              type="button"
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            
            <button 
              type="button"
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
            >
              <Mic className="w-5 h-5" />
            </button>
            
            <button 
              type="submit"
              disabled={!message.trim()}
              className={`p-2 rounded-full ${
                message.trim() 
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              } transition-colors`}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatInput;