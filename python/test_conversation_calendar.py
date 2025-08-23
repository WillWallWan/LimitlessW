#!/usr/bin/env python3
"""
Test Conversation Calendar Integration

Creates a 'Conversations' calendar and tests with one sample conversation.
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google_calendar_integration import GoogleCalendarTodoManager
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def create_test_conversation_event(calendar_manager, lifelog, calendar_id):
    """Create a test calendar event for a single conversation"""
    
    title = lifelog.get('title', 'Conversation')
    start_time = lifelog.get('startTime')
    end_time = lifelog.get('endTime')
    markdown = lifelog.get('markdown', '')
    
    if not start_time or not end_time:
        print(f"⚠️  Skipping '{title}' - missing time information")
        return None
    
    try:
        # Parse times
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Calculate duration
        duration = end_dt - start_dt
        duration_minutes = duration.total_seconds() / 60
        
        # Create event title
        event_title = f"💬 {title}"
        
        # Create event description with key info
        description = f"""Conversation Log from Limitless

📅 Duration: {duration_minutes:.1f} minutes
🗣️ Topic: {title}

📝 Content Summary:
{markdown[:500] + '...' if len(markdown) > 500 else markdown}

---
🤖 Auto-generated from Limitless conversation data
"""
        
        # Create the calendar event
        event = {
            'summary': event_title,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Adjust to your timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'colorId': '8',  # Light blue color for conversation events
            'transparency': 'transparent',  # Won't block other events
        }
        
        # Show preview first
        print(f"\n📋 Event Preview:")
        print(f"📅 Calendar: Conversations")
        print(f"🏷️  Title: {event_title}")
        print(f"⏰ Time: {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}")
        print(f"⏱️  Duration: {duration_minutes:.1f} minutes")
        print(f"📝 Description Preview:")
        print(f"   {description[:200]}...")
        
        # Ask for confirmation
        proceed = input(f"\nCreate this test event? (y/n): ").strip().lower()
        
        if proceed != 'y':
            print("⏸️  Test cancelled")
            return None
        
        try:
            event_result = calendar_manager.calendar_service.events().insert(
                calendarId=calendar_id, body=event).execute()
            
            time_str = start_dt.strftime("%I:%M %p")
            print(f"✅ {time_str} - {title[:50]} ({duration_minutes:.1f}m)")
            print(f"🔗 Event URL: {event_result.get('htmlLink')}")
            return event_result.get('id')
            
        except Exception as e:
            print(f"❌ Failed to create event for '{title}': {e}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing '{title}': {e}")
        return None

def test_conversation_calendar():
    """Test creating a conversation calendar with one sample event"""
    
    # Calculate yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")
    
    print("🧪 Test Conversation Calendar")
    print("=" * 50)
    print(f"🗓️  Testing with conversations from: {target_date}")
    
    # Check API keys
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print(f"\n📚 Fetching conversations...")
    
    try:
        # Get conversations for the target date (just first few)
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            date=target_date,
            includeMarkdown=True,
            direction="asc",
            limit=5  # Just get first 5 for testing
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {target_date}")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations (showing first 5)")
        
        # Initialize Google Calendar manager
        print(f"\n🔐 Authenticating with Google Calendar...")
        calendar_manager = GoogleCalendarTodoManager()
        
        if not calendar_manager.authenticate():
            print("❌ Google Calendar authentication failed!")
            return
        
        print("✅ Google Calendar connected!")
        
        # Create or find the Conversations calendar
        print(f"\n📅 Setting up 'Conversations' calendar...")
        calendar_id = calendar_manager.get_or_create_conversations_calendar()
        
        if not calendar_id:
            print("❌ Failed to create/find Conversations calendar")
            return
        
        # Filter for meaningful conversations and show options
        print(f"\n📋 Available conversations for testing:")
        print("-" * 40)
        
        meaningful_conversations = []
        for i, lifelog in enumerate(lifelogs):
            start_time = lifelog.get('startTime')
            end_time = lifelog.get('endTime')
            title = lifelog.get('title', 'Untitled')
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end_dt - start_dt
                    
                    # Only include conversations longer than 30 seconds
                    if duration.total_seconds() >= 30:
                        meaningful_conversations.append(lifelog)
                        time_str = start_dt.strftime("%I:%M %p")
                        duration_minutes = duration.total_seconds() / 60
                        print(f"  {len(meaningful_conversations):2d}. {time_str} - {title[:50]} ({duration_minutes:.1f}m)")
                except:
                    pass
        
        if not meaningful_conversations:
            print("📭 No meaningful conversations found for testing")
            return
        
        # Let user pick which conversation to test with
        try:
            choice = input(f"\nPick a conversation to test (1-{len(meaningful_conversations)}): ").strip()
            choice_idx = int(choice) - 1
            
            if choice_idx < 0 or choice_idx >= len(meaningful_conversations):
                print("❌ Invalid choice")
                return
                
        except ValueError:
            print("❌ Please enter a number")
            return
        
        # Test with selected conversation
        selected_conversation = meaningful_conversations[choice_idx]
        
        print(f"\n🎯 Testing with selected conversation...")
        print("=" * 40)
        
        event_id = create_test_conversation_event(calendar_manager, selected_conversation, calendar_id)
        
        if event_id:
            print(f"\n🎉 Test successful!")
            print("=" * 40)
            print(f"✅ Created test event in 'Conversations' calendar")
            print(f"📅 Check your Google Calendar to see how it looks")
            print(f"🎨 Should appear in light blue color")
            print(f"👻 Event is 'transparent' so won't block other events")
            
            print(f"\n💡 If this looks good, you can run the full import:")
            print(f"   python3 conversation_calendar_logger.py")
        else:
            print(f"\n❌ Test failed - check the error messages above")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_conversation_calendar()


