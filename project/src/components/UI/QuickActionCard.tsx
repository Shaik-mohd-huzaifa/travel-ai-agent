import React from 'react';
import { QuickAction } from '../../types';
import { Plane, Hotel, MapPin, Calendar } from 'lucide-react';

interface QuickActionCardProps {
  action: QuickAction;
}

const QuickActionCard: React.FC<QuickActionCardProps> = ({ action }) => {
  const getIcon = () => {
    switch (action.icon) {
      case 'Plane':
        return <Plane className="w-5 h-5 text-blue-600" />;
      case 'Hotel':
        return <Hotel className="w-5 h-5 text-green-600" />;
      case 'MapPin':
        return <MapPin className="w-5 h-5 text-amber-600" />;
      case 'Calendar':
        return <Calendar className="w-5 h-5 text-purple-600" />;
      default:
        return <Plane className="w-5 h-5 text-blue-600" />;
    }
  };

  return (
    <button className={`${action.color} p-4 rounded-xl hover:shadow-md transition-all flex flex-col items-center justify-center h-24`}>
      <div className="mb-2">
        {getIcon()}
      </div>
      <span className="text-sm font-medium text-gray-800">{action.title}</span>
    </button>
  );
};

export default QuickActionCard;