import React from 'react';
import { Message } from '../../types';
import { Globe } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isAI = message.sender === 'ai';
  
  return (
    <div className={`flex ${isAI ? 'justify-start' : 'justify-end'} mb-4 animate-fadeIn`}>
      {isAI && (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center mr-2 flex-shrink-0">
          <Globe className="w-4 h-4 text-white" />
        </div>
      )}
      
      <div className={`max-w-[80%] px-4 py-3 rounded-2xl ${
        isAI 
          ? 'bg-white text-gray-800 shadow-sm' 
          : 'bg-indigo-600 text-white'
      }`}>
        {isAI ? (
          <div className="markdown-content">
            <ReactMarkdown>
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
        
        {/* Display flight and hotel details if available in raw data */}
        {isAI && message.rawData && (
          <div className="mt-4 pt-4 border-t border-gray-200 text-sm">
            {message.rawData.flights && message.rawData.flights.length > 0 && (
              <div className="mb-2">
                <strong>Available Flights:</strong> {message.rawData.flights.length}
              </div>
            )}
            {message.rawData.hotels && message.rawData.hotels.length > 0 && (
              <div>
                <strong>Available Hotels:</strong> {message.rawData.hotels.length}
              </div>
            )}
          </div>
        )}
      </div>
      
      {!isAI && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center ml-2 flex-shrink-0">
          <span className="text-sm font-medium text-gray-700">You</span>
        </div>
      )}
    </div>
  );
};

export default MessageBubble;