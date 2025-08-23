import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables from .env file
load_dotenv()

class TodoExtractor:
    """Extract action items and todos from Limitless conversation data"""
    
    def __init__(self):
        # Patterns that indicate action items
        self.action_patterns = [
            r"I need to (.+?)(?:\.|$|,|\n)",
            r"I'll (.+?)(?:\.|$|,|\n)", 
            r"I should (.+?)(?:\.|$|,|\n)",
            r"I have to (.+?)(?:\.|$|,|\n)",
            r"I'm going to (.+?)(?:\.|$|,|\n)",
            r"TODO:? (.+?)(?:\.|$|,|\n)",
            r"Action item:? (.+?)(?:\.|$|,|\n)",
            r"Follow up (.+?)(?:\.|$|,|\n)",
            r"Remember to (.+?)(?:\.|$|,|\n)",
            r"Don't forget to (.+?)(?:\.|$|,|\n)",
            r"Make sure to (.+?)(?:\.|$|,|\n)",
        ]
        
        # Patterns for urgency/timing
        self.urgency_patterns = {
            'today': r'\b(today|this afternoon|this evening|tonight)\b',
            'tomorrow': r'\b(tomorrow|tomorrow morning)\b', 
            'this_week': r'\b(this week|by friday|end of week)\b',
            'next_week': r'\b(next week|monday)\b',
            'urgent': r'\b(urgent|asap|immediately|right away|as soon as possible)\b'
        }
        
        # Category patterns
        self.category_patterns = {
            'work': r'\b(meeting|email|call|project|client|deadline|presentation|report)\b',
            'personal': r'\b(doctor|appointment|family|friend|groceries|shopping)\b',
            'health': r'\b(doctor|dentist|gym|exercise|medication|checkup)\b',
            'finance': r'\b(pay|bill|tax|bank|insurance|budget)\b',
            'home': r'\b(clean|fix|repair|maintenance|groceries|chores)\b'
        }
    
    def extract_todos_from_lifelogs(self, lifelogs: List[Dict]) -> List[Dict]:
        """Extract todos from a list of lifelogs"""
        all_todos = []
        
        for lifelog in lifelogs:
            todos = self.extract_todos_from_lifelog(lifelog)
            all_todos.extend(todos)
            
        return all_todos
    
    def extract_todos_from_lifelog(self, lifelog: Dict) -> List[Dict]:
        """Extract todos from a single lifelog"""
        todos = []
        markdown = lifelog.get('markdown', '')
        
        if not markdown:
            return todos
            
        # Extract action items using patterns
        for pattern in self.action_patterns:
            matches = re.finditer(pattern, markdown, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                todo_text = match.group(1).strip()
                
                # Skip if too short or looks like incomplete sentence
                if len(todo_text) < 5 or todo_text.lower() in ['it', 'that', 'this']:
                    continue
                
                todo = {
                    'text': todo_text,
                    'full_context': match.group(0),
                    'lifelog_id': lifelog.get('id'),
                    'lifelog_title': lifelog.get('title'),
                    'source_time': lifelog.get('startTime'),
                    'urgency': self._detect_urgency(markdown, match.start()),
                    'category': self._detect_category(todo_text),
                    'extracted_at': datetime.now().isoformat()
                }
                
                todos.append(todo)
        
        return todos
    
    def _detect_urgency(self, text: str, match_position: int) -> str:
        """Detect urgency level based on surrounding context"""
        # Look at text around the match (±100 characters)
        start = max(0, match_position - 100)
        end = min(len(text), match_position + 100)
        context = text[start:end].lower()
        
        for urgency, pattern in self.urgency_patterns.items():
            if re.search(pattern, context, re.IGNORECASE):
                return urgency
                
        return 'normal'
    
    def _detect_category(self, todo_text: str) -> str:
        """Detect category based on todo content"""
        text = todo_text.lower()
        
        for category, pattern in self.category_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return category
                
        return 'general'
    
    def deduplicate_todos(self, todos: List[Dict]) -> List[Dict]:
        """Remove duplicate todos based on similarity"""
        unique_todos = []
        seen_texts = set()
        
        for todo in todos:
            # Simple deduplication - check if similar text already exists
            text_normalized = todo['text'].lower().strip()
            
            # Check for exact duplicates
            if text_normalized in seen_texts:
                continue
                
            # Check for very similar todos (basic similarity)
            is_duplicate = False
            for seen_text in seen_texts:
                if self._are_similar_todos(text_normalized, seen_text):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_todos.append(todo)
                seen_texts.add(text_normalized)
        
        return unique_todos
    
    def _are_similar_todos(self, text1: str, text2: str) -> bool:
        """Check if two todo texts are similar enough to be considered duplicates"""
        # Basic similarity check - if one is contained in the other and they're close in length
        if text1 in text2 or text2 in text1:
            if abs(len(text1) - len(text2)) < 10:
                return True
        return False

def main():
    """Main function to extract todos from recent conversations"""
    
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("❌ Please set LIMITLESS_API_KEY environment variable")
        return
    
    print("🔍 Fetching recent conversations...")
    
    # Get recent lifelogs (last 7 days worth)
    lifelogs = get_lifelogs(
        api_key=api_key,
        limit=50,  # Adjust based on how much data you have
        direction="desc",
        includeMarkdown=True
    )
    
    print(f"📚 Found {len(lifelogs)} conversations")
    
    # Extract todos
    extractor = TodoExtractor()
    todos = extractor.extract_todos_from_lifelogs(lifelogs)
    
    print(f"📝 Found {len(todos)} potential action items")
    
    # Deduplicate
    unique_todos = extractor.deduplicate_todos(todos)
    
    print(f"✨ After deduplication: {len(unique_todos)} unique todos")
    
    # Display results
    for i, todo in enumerate(unique_todos, 1):
        print(f"\n--- Todo #{i} ---")
        print(f"📋 Task: {todo['text']}")
        print(f"🏷️  Category: {todo['category']}")
        print(f"⚡ Urgency: {todo['urgency']}")
        print(f"📅 From conversation: {todo['lifelog_title']}")
        print(f"🕐 Mentioned at: {todo['source_time']}")
        print(f"💬 Context: {todo['full_context'][:100]}...")
    
    # Save to file for later processing
    with open('extracted_todos.json', 'w') as f:
        json.dump(unique_todos, f, indent=2)
    
    print(f"\n💾 Saved {len(unique_todos)} todos to 'extracted_todos.json'")
    print("📅 Next: Set up Google Calendar integration to create events!")

if __name__ == "__main__":
    main()
