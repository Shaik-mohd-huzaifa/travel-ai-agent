import React from 'react';
import { Share, Settings } from 'lucide-react';

const ChatHeader = () => {
  return (
    <div className="h-16 px-6 border-b border-gray-200 flex items-center justify-between bg-white">
      <div className="flex items-center">
        <h1 className="text-lg font-medium">Travel AI</h1>
        <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">Plus</span>
      </div>
      
      <div className="flex items-center space-x-4">
        <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors">
          <Settings className="w-5 h-5" />
        </button>
        
        <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors">
          <Share className="w-5 h-5" />
        </button>
        
        <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center space-x-2">
          <span>New Chat</span>
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;