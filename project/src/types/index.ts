export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  rawData?: any; // Optional field to store structured data from API responses
}

export interface QuickAction {
  id: string;
  title: string;
  icon: string;
  color: string;
}

export interface Suggestion {
  id: string;
  content: string;
}