#!/usr/bin/env python3
"""
Yesterday's Todo Extraction

Automatically gets yesterday's date and extracts todos from those conversations only.
Perfect for daily review of what you discussed yesterday.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from todo_tracker import TodoExtractor, get_lifelogs

# Load environment variables
load_dotenv()

def get_yesterday_todos():
    """Extract todos from yesterday's conversations specifically"""
    
    # Calculate yesterday's date
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    print("📅 Yesterday's Todo Extraction")
    print("=" * 50)
    print(f"🗓️  Today: {today}")
    print(f"🗓️  Yesterday: {yesterday} ({yesterday_str})")
    
    # Check API key
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print(f"\n🔍 Fetching conversations from {yesterday_str}...")
    
    try:
        # Get yesterday's conversations only
        lifelogs = get_lifelogs(
            api_key=api_key,
            date=yesterday_str,  # This gets only conversations from yesterday
            includeMarkdown=True,
            direction="asc"  # Chronological order for daily review
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {yesterday_str}")
            print("💡 This could mean:")
            print("   • No recordings on that day")
            print("   • Date format issue")
            print("   • Timezone differences")
            return
        
        print(f"📚 Found {len(lifelogs)} conversations from yesterday")
        
        # Show conversation overview
        print(f"\n🕐 **Yesterday's Conversation Timeline:**")
        print("-" * 50)
        
        total_duration_minutes = 0
        for i, lifelog in enumerate(lifelogs, 1):
            title = lifelog.get('title', 'Untitled')
            start_time = lifelog.get('startTime', 'Unknown')
            end_time = lifelog.get('endTime', 'Unknown')
            
            # Extract just the time part (HH:MM)
            if start_time != 'Unknown':
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = start_dt.strftime("%I:%M %p")
                    
                    if end_time != 'Unknown':
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        duration = end_dt - start_dt
                        duration_min = duration.total_seconds() / 60
                        total_duration_minutes += duration_min
                        print(f"  {i:2d}. {time_str:8s} - {title[:45]} ({duration_min:.1f}m)")
                    else:
                        print(f"  {i:2d}. {time_str:8s} - {title[:45]}")
                except:
                    print(f"  {i:2d}. {start_time:8s} - {title[:45]}")
            else:
                print(f"  {i:2d}. Unknown - {title[:45]}")
        
        print(f"\n📊 Total conversation time: {total_duration_minutes:.1f} minutes")
        
        # Extract todos
        print(f"\n🔍 Extracting action items from yesterday's conversations...")
        
        extractor = TodoExtractor()
        todos = extractor.extract_todos_from_lifelogs(lifelogs)
        
        print(f"📝 Found {len(todos)} potential action items")
        
        # Deduplicate
        unique_todos = extractor.deduplicate_todos(todos)
        
        print(f"✨ After deduplication: {len(unique_todos)} unique todos")
        
        if not unique_todos:
            print("📭 No action items found in yesterday's conversations!")
            print("💡 Try phrases like:")
            print("   • 'I need to...'")
            print("   • 'I'll follow up...'") 
            print("   • 'TODO: ...'")
            print("   • 'I should...'")
            return
        
        # Display todos organized by urgency
        print(f"\n📋 **Yesterday's Action Items:**")
        print("=" * 60)
        
        # Group by urgency
        urgency_groups = {
            'urgent': [],
            'today': [],
            'tomorrow': [],
            'this_week': [],
            'normal': []
        }
        
        for todo in unique_todos:
            urgency = todo.get('urgency', 'normal')
            urgency_groups[urgency].append(todo)
        
        # Display by urgency level
        urgency_labels = {
            'urgent': '🚨 URGENT',
            'today': '📅 TODAY',
            'tomorrow': '🗓️  TOMORROW', 
            'this_week': '📆 THIS WEEK',
            'normal': '📝 GENERAL'
        }
        
        for urgency, label in urgency_labels.items():
            todos_in_group = urgency_groups[urgency]
            if todos_in_group:
                print(f"\n{label}:")
                print("-" * 30)
                for i, todo in enumerate(todos_in_group, 1):
                    category = todo.get('category', 'general').upper()
                    source_time = todo.get('source_time', 'Unknown')
                    lifelog_title = todo.get('lifelog_title', 'Unknown conversation')
                    
                    # Extract time from source
                    time_str = "Unknown time"
                    if source_time != 'Unknown':
                        try:
                            dt = datetime.fromisoformat(source_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%I:%M %p")
                        except:
                            time_str = source_time[:5]  # Just show first 5 chars
                    
                    print(f"  {i}. [{category}] {todo['text']}")
                    print(f"     ⏰ Mentioned at {time_str}")
                    print(f"     💬 From: {lifelog_title[:40]}{'...' if len(lifelog_title) > 40 else ''}")
                    print()
        
        # Summary
        print(f"📊 **Summary for {yesterday_str}:**")
        print("-" * 50)
        print(f"   • {len(lifelogs)} conversations analyzed")
        print(f"   • {total_duration_minutes:.1f} minutes of conversation time")
        print(f"   • {len(unique_todos)} unique action items extracted")
        
        # Save for further processing
        import json
        filename = f"yesterday_todos_{yesterday_str}.json"
        with open(filename, 'w') as f:
            json.dump(unique_todos, f, indent=2)
        
        print(f"   • Saved to {filename} for calendar integration")
        
        print(f"\n💡 **Next Steps:**")
        print(f"   • Review action items above")
        print(f"   • Run calendar integration: python3 limitless_todo_calendar.py")
        print(f"   • Get AI analysis: python3 claude_gentle_summary.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def get_specific_date_todos(date_str):
    """Get todos for a specific date (YYYY-MM-DD format)"""
    
    print(f"📅 Todo Extraction for {date_str}")
    print("=" * 50)
    
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print(f"🔍 Fetching conversations from {date_str}...")
    
    try:
        lifelogs = get_lifelogs(
            api_key=api_key,
            date=date_str,
            includeMarkdown=True,
            direction="asc"
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {date_str}")
            return
        
        print(f"📚 Found {len(lifelogs)} conversations")
        
        # Extract and display todos (same logic as above)
        extractor = TodoExtractor()
        todos = extractor.extract_todos_from_lifelogs(lifelogs)
        unique_todos = extractor.deduplicate_todos(todos)
        
        print(f"✨ Found {len(unique_todos)} unique action items")
        
        for i, todo in enumerate(unique_todos, 1):
            category = todo.get('category', 'general').upper()
            urgency = todo.get('urgency', 'normal').upper()
            print(f"  {i}. [{category}] [{urgency}] {todo['text']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Specific date provided
        date_arg = sys.argv[1]
        get_specific_date_todos(date_arg)
    else:
        # Default to yesterday
        get_yesterday_todos()


