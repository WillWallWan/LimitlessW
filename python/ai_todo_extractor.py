#!/usr/bin/env python3
"""
AI-Powered Todo Extraction

Uses Claude to intelligently parse conversations and extract real action items,
instead of just keyword matching. Much more accurate!
"""

import os
import json
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def extract_todos_with_ai(lifelogs, date_context="recent conversations"):
    """Use Claude to intelligently extract todos from conversations"""
    
    # Get Claude API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        return []
    
    client = Anthropic(api_key=api_key)
    
    # Prepare conversation content for Claude
    conversation_content = ""
    conversation_metadata = []
    
    for i, lifelog in enumerate(lifelogs, 1):
        title = lifelog.get('title', f'Conversation {i}')
        start_time = lifelog.get('startTime', 'Unknown')
        markdown = lifelog.get('markdown', '')
        
        # Format time nicely
        time_str = "Unknown time"
        if start_time != 'Unknown':
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = dt.strftime("%I:%M %p")
            except:
                time_str = start_time[:10]
        
        conversation_content += f"\n--- Conversation {i}: {title} ({time_str}) ---\n"
        conversation_content += markdown + "\n"
        
        conversation_metadata.append({
            'id': lifelog.get('id'),
            'title': title,
            'time': time_str,
            'start_time': start_time
        })
    
    # Create the AI prompt
    prompt = f"""I need you to analyze these conversation transcripts from {date_context} and extract REAL action items that the speaker needs to do.

IMPORTANT GUIDELINES:
1. Only extract items that are genuine commitments, tasks, or things the person said they need/want to do
2. Ignore casual conversation, opinions, or hypothetical statements
3. Rephrase vague items to be more actionable and clear
4. Include context about timing/urgency if mentioned
5. Categorize each item (work, personal, health, finance, shopping, etc.)
6. Return results as a JSON array

For each real action item, provide:
- "task": Clear, actionable description
- "urgency": "urgent", "today", "tomorrow", "this_week", or "normal"
- "category": "work", "personal", "health", "finance", "shopping", "home", etc.
- "context": Brief context from the conversation
- "conversation_number": Which conversation it came from (1, 2, 3, etc.)
- "confidence": "high", "medium", or "low" - how confident you are this is a real action item

EXAMPLE OUTPUT FORMAT:
```json
[
  {{
    "task": "Update LinkedIn profile title",
    "urgency": "normal",
    "category": "work",
    "context": "Mentioned wanting to change LinkedIn title during evening conversation",
    "conversation_number": 3,
    "confidence": "high"
  }},
  {{
    "task": "Buy rice and pork chop for meal",
    "urgency": "today",
    "category": "shopping",
    "context": "Specific food items mentioned during lunch planning",
    "conversation_number": 1,
    "confidence": "high"
  }}
]
```

Conversation Transcripts:
{conversation_content}

Please analyze these conversations and extract only the genuine action items as JSON:"""

    try:
        print("🤖 Claude is analyzing conversations for real action items...")
        
        # Get AI response
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        print("✅ Claude analysis complete!")
        
        # Extract JSON from response
        try:
            # Find JSON array in the response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                todos = json.loads(json_str)
                
                # Add metadata to each todo
                for todo in todos:
                    conv_num = todo.get('conversation_number', 1)
                    if 1 <= conv_num <= len(conversation_metadata):
                        metadata = conversation_metadata[conv_num - 1]
                        todo['lifelog_id'] = metadata['id']
                        todo['lifelog_title'] = metadata['title']
                        todo['source_time'] = metadata['start_time']
                
                return todos
            else:
                print("❌ Could not find JSON in Claude's response")
                print("Claude's response:", response_text[:500])
                return []
                
        except json.JSONDecodeError as e:
            print(f"❌ Could not parse Claude's JSON response: {e}")
            print("Response:", response_text[:500])
            return []
            
    except Exception as e:
        print(f"❌ Error with Claude API: {e}")
        return []

def analyze_yesterday_with_ai():
    """Get yesterday's conversations and analyze with AI"""
    
    # Calculate yesterday's date
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    print("🤖 AI-Powered Yesterday's Todo Analysis")
    print("=" * 60)
    print(f"🗓️  Analyzing conversations from: {yesterday_str}")
    
    # Check API keys
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    if not claude_key:
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        return
    
    print(f"\n📚 Fetching conversations from {yesterday_str}...")
    
    try:
        # Get yesterday's conversations
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            date=yesterday_str,
            includeMarkdown=True,
            direction="asc"
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {yesterday_str}")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations")
        
        # Show conversation overview
        total_duration = 0
        print(f"\n📋 **Conversation Overview:**")
        print("-" * 50)
        
        for i, lifelog in enumerate(lifelogs[:5], 1):  # Show first 5
            title = lifelog.get('title', 'Untitled')
            start_time = lifelog.get('startTime', 'Unknown')
            end_time = lifelog.get('endTime', 'Unknown')
            
            if start_time != 'Unknown' and end_time != 'Unknown':
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end_dt - start_dt
                    duration_min = duration.total_seconds() / 60
                    total_duration += duration_min
                    time_str = start_dt.strftime("%I:%M %p")
                    print(f"  {i}. {time_str} - {title[:50]} ({duration_min:.1f}m)")
                except:
                    print(f"  {i}. {title[:50]}")
            else:
                print(f"  {i}. {title[:50]}")
        
        if len(lifelogs) > 5:
            print(f"  ... and {len(lifelogs) - 5} more conversations")
        
        # Extract todos with AI
        print(f"\n🤖 Using Claude to extract real action items...")
        todos = extract_todos_with_ai(lifelogs, f"yesterday's conversations ({yesterday_str})")
        
        if not todos:
            print("❌ No action items extracted - there may have been an error")
            return
        
        print(f"✨ Claude found {len(todos)} genuine action items!")
        
        # Display results organized by confidence and urgency
        print(f"\n📋 **AI-Extracted Action Items:**")
        print("=" * 60)
        
        # Group by confidence
        high_confidence = [t for t in todos if t.get('confidence') == 'high']
        medium_confidence = [t for t in todos if t.get('confidence') == 'medium']
        low_confidence = [t for t in todos if t.get('confidence') == 'low']
        
        for confidence_level, items in [
            ("🎯 HIGH CONFIDENCE", high_confidence),
            ("🤔 MEDIUM CONFIDENCE", medium_confidence),
            ("❓ LOW CONFIDENCE", low_confidence)
        ]:
            if items:
                print(f"\n{confidence_level} ({len(items)} items):")
                print("-" * 40)
                
                # Sort by urgency
                urgency_order = {'urgent': 0, 'today': 1, 'tomorrow': 2, 'this_week': 3, 'normal': 4}
                items.sort(key=lambda x: urgency_order.get(x.get('urgency', 'normal'), 4))
                
                for i, todo in enumerate(items, 1):
                    urgency = todo.get('urgency', 'normal').upper()
                    category = todo.get('category', 'general').upper()
                    task = todo.get('task', 'Unknown task')
                    context = todo.get('context', 'No context')
                    conv_num = todo.get('conversation_number', '?')
                    
                    print(f"  {i}. [{urgency}] [{category}] {task}")
                    print(f"     💬 Context: {context}")
                    print(f"     📍 From conversation #{conv_num}")
                    print()
        
        # Save results
        filename = f"ai_todos_{yesterday_str}.json"
        with open(filename, 'w') as f:
            json.dump(todos, f, indent=2)
        
        print(f"📊 **Summary:**")
        print("-" * 40)
        print(f"   • {len(lifelogs)} conversations analyzed")
        print(f"   • {len(todos)} AI-extracted action items")
        print(f"   • {len(high_confidence)} high-confidence items")
        print(f"   • Saved to {filename}")
        
        print(f"\n💡 **Why AI is better:**")
        print(f"   • Understands context vs. casual speech")
        print(f"   • Rephrases vague items clearly")
        print(f"   • Filters out conversational fragments")
        print(f"   • Provides confidence levels")
        print(f"   • Smart categorization and urgency detection")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def analyze_specific_date_with_ai(date_str):
    """Analyze a specific date with AI"""
    
    print(f"🤖 AI-Powered Todo Analysis for {date_str}")
    print("=" * 60)
    
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print(f"📚 Fetching conversations from {date_str}...")
    
    try:
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            date=date_str,
            includeMarkdown=True,
            direction="asc"
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {date_str}")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations")
        
        # Extract with AI
        todos = extract_todos_with_ai(lifelogs, f"conversations from {date_str}")
        
        if todos:
            print(f"✨ Found {len(todos)} action items!")
            
            # Quick display
            for i, todo in enumerate(todos, 1):
                urgency = todo.get('urgency', 'normal').upper()
                category = todo.get('category', 'general').upper()
                confidence = todo.get('confidence', 'unknown').upper()
                task = todo.get('task', 'Unknown task')
                print(f"  {i}. [{confidence}] [{urgency}] [{category}] {task}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Specific date provided
        date_arg = sys.argv[1]
        analyze_specific_date_with_ai(date_arg)
    else:
        # Default to yesterday
        analyze_yesterday_with_ai()


