import { useState, useRef } from 'react';
import ChatHeader from './ChatHeader';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import WelcomeSection from './WelcomeSection';
import { Message } from '../../types';
import { initialMessages } from '../../data/mockData';
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';

// API configuration
const API_URL = 'http://localhost:8000/api/amadeus-agent/';

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;
    
    const userMessage: Message = {
      id: uuidv4(),
      content,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);
    
    try {
      // Make API call to the Amadeus Trip Planner endpoint
      const response = await axios.post(API_URL, {
        message: content
      }, {
        headers: {
          'Content-Type': 'application/json',
          // Authentication temporarily disabled on backend for development
          // 'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      const aiResponse: Message = {
        id: uuidv4(),
        content: response.data.response || "Sorry, I couldn't process your request.",
        sender: 'ai',
        timestamp: new Date(),
        rawData: response.data.raw_data // Store raw data for potential UI enhancements
      };
      
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error('Error fetching response:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        content: "I'm sorry, I encountered an error processing your request. Please try again later.",
        sender: 'ai',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestionSelect = (content: string) => {
    setInputValue(content);
    // Focus the input field
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Show welcome section only when there's just the initial greeting message
  const showWelcomeSection = messages.length <= 1;

  return (
    <div className="flex-1 flex flex-col h-screen ml-[80px]">
      <ChatHeader />
      <div className="flex-1 overflow-y-auto pb-32">
        {showWelcomeSection ? (
          <WelcomeSection onSuggestionSelect={handleSuggestionSelect} />
        ) : (
          <ChatMessages messages={messages} isTyping={isTyping} />
        )}
      </div>
      <ChatInput 
        onSendMessage={handleSendMessage} 
        inputValue={inputValue}
        setInputValue={setInputValue}
        inputRef={inputRef}
      />
    </div>
  );
};

export default ChatInterface;