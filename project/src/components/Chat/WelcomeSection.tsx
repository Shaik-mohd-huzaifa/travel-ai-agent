import React from 'react';
import { Globe } from 'lucide-react';
import QuickActionCard from '../UI/QuickActionCard';
import SuggestionCard from '../UI/SuggestionCard';
import { quickActions, travelSuggestions } from '../../data/mockData';

interface WelcomeSectionProps {
  onSuggestionSelect?: (content: string) => void;
}

const WelcomeSection: React.FC<WelcomeSectionProps> = ({ onSuggestionSelect }) => {
  return (
    <div className="flex flex-col items-center justify-center py-8 space-y-6">
      <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center mb-2">
        <Globe className="w-8 h-8 text-blue-500" />
      </div>
      
      <h2 className="text-2xl font-bold text-gray-800">Hi, there 👋</h2>
      <p className="text-gray-600 text-center max-w-md">
        Tell us what you need, and we'll handle the rest of your travel plans.
      </p>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-3xl mt-6">
        {quickActions.map(action => (
          <QuickActionCard key={action.id} action={action} />
        ))}
      </div>
      
      <div className="w-full max-w-3xl mt-6">
        <h3 className="text-sm font-medium text-gray-500 mb-3">Suggested trip planners</h3>
        <div className="space-y-2">
          {travelSuggestions.map(suggestion => (
            <SuggestionCard 
              key={suggestion.id} 
              suggestion={suggestion} 
              onSelect={onSuggestionSelect}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default WelcomeSection;