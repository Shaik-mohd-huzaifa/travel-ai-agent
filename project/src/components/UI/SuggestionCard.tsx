import React from 'react';
import { Suggestion } from '../../types';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onSelect?: (content: string) => void;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({ suggestion, onSelect }) => {
  const handleClick = () => {
    if (onSelect) {
      onSelect(suggestion.content);
    }
  };

  return (
    <button 
      className="w-full text-left p-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      onClick={handleClick}
    >
      <p className="text-gray-800">{suggestion.content}</p>
    </button>
  );
};

export default SuggestionCard;