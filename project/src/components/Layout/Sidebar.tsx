import React, { useState } from 'react';
import { sidebarIcons } from '../../data/mockData';
import { Globe, Settings, User, ChevronRight, ChevronLeft } from 'lucide-react';

const Sidebar = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`sidebar fixed h-full bg-white flex flex-col items-center py-6 border-r border-gray-200 ${isExpanded ? 'sidebar-expanded' : 'w-[80px]'}`}>
      <div className="mb-6 flex items-center justify-between w-full px-6">
        <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center text-white">
          <Globe className="w-5 h-5" />
        </div>
        {isExpanded && <span className="font-medium text-gray-900">Travel AI</span>}
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-3 top-8 w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-500 hover:text-gray-900 transition-colors"
      >
        {isExpanded ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      <div className="flex flex-col w-full">
        {sidebarIcons.map((item, index) => (
          <button 
            key={index}
            className={`w-full flex items-center px-6 py-3
              ${item.active 
                ? 'bg-indigo-100 text-indigo-600' 
                : 'text-gray-500 hover:bg-gray-100'}`}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {isExpanded && <span className="ml-3 text-sm">{item.label}</span>}
          </button>
        ))}
      </div>

      <div className="mt-auto flex flex-col w-full px-6">
        <button className="w-full flex items-center py-3 text-gray-500 hover:bg-gray-100">
          <Settings className="w-5 h-5 flex-shrink-0" />
          {isExpanded && <span className="ml-3 text-sm">Settings</span>}
        </button>
        <button className="mt-4 w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
          <User className="w-5 h-5 text-gray-700" />
        </button>
      </div>
    </div>
  );
};

export default Sidebar;