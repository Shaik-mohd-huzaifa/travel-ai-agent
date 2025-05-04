import React, { useEffect, useRef } from 'react';
import { Message } from '../../types';
import MessageBubble from './MessageBubble';
import WelcomeSection from './WelcomeSection';
import { Loader2 } from 'lucide-react';

interface ChatMessagesProps {
  messages: Message[];
  isTyping: boolean;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, isTyping }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Show welcome screen if we only have the initial AI message
  const showWelcome = messages.length === 1 && messages[0].sender === 'ai';

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
      {showWelcome ? (
        <WelcomeSection />
      ) : (
        <>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </>
      )}
      
      {isTyping && (
        <div className="flex items-center space-x-2 text-gray-500 animate-pulse">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">AI is typing...</span>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;