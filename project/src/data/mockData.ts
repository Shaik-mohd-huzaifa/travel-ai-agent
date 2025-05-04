import { Message, QuickAction, Suggestion } from '../types';
import { 
  Plane, Hotel, Calendar, Compass, 
  Palmtree, CreditCard, Briefcase
} from 'lucide-react';

export const initialMessages: Message[] = [
  {
    id: '1',
    content: "Hi there 👋\n\nI'm your AI Travel Assistant. How can I help with your travel plans today?",
    sender: 'ai',
    timestamp: new Date()
  }
];

export const quickActions: QuickAction[] = [
  {
    id: '1',
    title: 'Find Flights',
    icon: 'Plane',
    color: 'bg-blue-100'
  },
  {
    id: '2',
    title: 'Browse Hotels',
    icon: 'Hotel',
    color: 'bg-green-100'
  },
  {
    id: '3',
    title: 'Explore Destinations',
    icon: 'MapPin',
    color: 'bg-amber-100'
  },
  {
    id: '4',
    title: 'Travel Itineraries',
    icon: 'Calendar',
    color: 'bg-purple-100'
  }
];

export const travelSuggestions: Suggestion[] = [
  {
    id: '1',
    content: 'Plan a trip to Paris from June 15 to June 22, 2025'
  },
  {
    id: '2',
    content: 'I need a luxury vacation in Barcelona for a week in August'
  },
  {
    id: '3',
    content: 'Find me a budget hotel in Tokyo for 5 days in July'
  },
  {
    id: '4',
    content: 'What are the best activities to do in New York City?'
  }
];

export const sidebarIcons = [
  { icon: Compass, active: true, label: 'Explore' },
  { icon: Plane, label: 'Flights' },
  { icon: Hotel, label: 'Hotels' },
  { icon: Calendar, label: 'Itinerary' },
  { icon: Palmtree, label: 'Activities' },
  { icon: CreditCard, label: 'Payments' },
  { icon: Briefcase, label: 'Bookings' }
];