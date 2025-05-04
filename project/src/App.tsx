import React from 'react';
import Sidebar from './components/Layout/Sidebar';
import ChatInterface from './components/Chat/ChatInterface';

function App() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <ChatInterface />
    </div>
  );
}

export default App;