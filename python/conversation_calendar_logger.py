#!/usr/bin/env python3
"""
Conversation Calendar Logger

Creates Google Calendar events for each conversation from your Limitless lifelogs.
Simple approach: One calendar event per conversation with title, time, and summary.
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google_calendar_integration import GoogleCalendarTodoManager
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def create_conversation_event(calendar_manager, lifelog, calendar_id='primary'):
    """Create a calendar event for a single conversation"""
    
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
                'timeZone': 'America/New_York',  # Adjust to your timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
            'colorId': '8',  # Light blue color for conversation events
            'transparency': 'transparent',  # Won't block other events
        }
        
        try:
            event_result = calendar_manager.calendar_service.events().insert(
                calendarId=calendar_id, body=event).execute()
            
            time_str = start_dt.strftime("%I:%M %p")
            print(f"✅ {time_str} - {title[:50]} ({duration_minutes:.1f}m)")
            return event_result.get('id')
            
        except Exception as e:
            print(f"❌ Failed to create event for '{title}': {e}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing '{title}': {e}")
        return None

def log_conversations_to_calendar():
    """Main function to create calendar events for all conversations"""
    
    # Calculate yesterday (or change to today if you want)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")
    
    print("📅 Conversation Calendar Logger")
    print("=" * 50)
    print(f"🗓️  Creating calendar events for: {target_date}")
    
    # Check API keys
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print(f"\n📚 Fetching conversations...")
    
    try:
        # Get conversations for the target date
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            date=target_date,
            includeMarkdown=True,
            direction="asc"  # Chronological order
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {target_date}")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations")
        
        # Initialize Google Calendar manager
        print(f"\n🔐 Authenticating with Google Calendar...")
        calendar_manager = GoogleCalendarTodoManager()
        
        if not calendar_manager.authenticate():
            print("❌ Google Calendar authentication failed!")
            print("\n📋 Setup Instructions:")
            print("1. Make sure credentials.json is in this directory")
            print("2. Enable Google Calendar API in Google Cloud Console")
            print("3. Run the script again to complete OAuth flow")
            return
        
        print("✅ Google Calendar connected!")
        
        # Create or find the Conversations calendar
        print(f"\n📅 Setting up 'Conversations' calendar...")
        conversations_calendar_id = calendar_manager.get_or_create_conversations_calendar()
        
        if not conversations_calendar_id:
            print("❌ Failed to create/find Conversations calendar")
            return
        
        # Filter out very short conversations (less than 30 seconds)
        meaningful_conversations = []
        for lifelog in lifelogs:
            start_time = lifelog.get('startTime')
            end_time = lifelog.get('endTime')
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end_dt - start_dt
                    
                    # Only include conversations longer than 30 seconds
                    if duration.total_seconds() >= 30:
                        meaningful_conversations.append(lifelog)
                except:
                    pass
        
        print(f"\n📝 Creating calendar events for {len(meaningful_conversations)} meaningful conversations...")
        print(f"(Filtered out {len(lifelogs) - len(meaningful_conversations)} very short conversations)")
        
        # Ask for confirmation
        proceed = input(f"\nCreate {len(meaningful_conversations)} calendar events? (y/n): ").strip().lower()
        
        if proceed != 'y':
            print("⏸️  Operation cancelled")
            return
        
        # Create calendar events
        created_count = 0
        
        print(f"\n🎯 Creating calendar events...")
        print("-" * 40)
        
        for lifelog in meaningful_conversations:
            event_id = create_conversation_event(calendar_manager, lifelog, conversations_calendar_id)
            if event_id:
                created_count += 1
        
        # Summary
        print(f"\n🎉 Calendar logging complete!")
        print("=" * 40)
        print(f"📊 Summary:")
        print(f"   • {len(lifelogs)} total conversations found")
        print(f"   • {len(meaningful_conversations)} meaningful conversations processed")
        print(f"   • {created_count} calendar events created")
        print(f"   • {len(meaningful_conversations) - created_count} events failed")
        
        print(f"\n📅 Check your Google Calendar for conversation events!")
        print(f"   • Events are marked with 💬 emoji")
        print(f"   • Light blue color coding")
        print(f"   • Set as 'transparent' so they don't block other events")
        print(f"   • Include conversation duration and content summary")
        
        if created_count > 0:
            print(f"\n💡 Pro tips:")
            print(f"   • Events are searchable in Google Calendar")
            print(f"   • Click any event to see full conversation context")
            print(f"   • Perfect for remembering 'what did I discuss when?'")
            print(f"   • Great for meeting follow-ups and relationship tracking")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def log_specific_date(date_str):
    """Log conversations for a specific date"""
    
    print("📅 Conversation Calendar Logger")
    print("=" * 50)
    print(f"🗓️  Creating calendar events for: {date_str}")
    
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
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
        
        # Quick summary without creating events
        print(f"\n📋 Conversation Preview:")
        print("-" * 40)
        
        for i, lifelog in enumerate(lifelogs, 1):
            title = lifelog.get('title', 'Untitled')
            start_time = lifelog.get('startTime', 'Unknown')
            
            time_str = "Unknown"
            if start_time != 'Unknown':
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime("%I:%M %p")
                except:
                    pass
            
            print(f"  {i:2d}. {time_str} - {title[:60]}")
        
        print(f"\nTo create calendar events, run with confirmation.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Specific date provided
        date_arg = sys.argv[1]
        if date_arg == "preview":
            # Just preview, don't create events
            log_specific_date((datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d"))
        else:
            log_specific_date(date_arg)
    else:
        # Default to yesterday and actually create events
        log_conversations_to_calendar()
