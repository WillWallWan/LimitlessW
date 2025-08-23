#!/usr/bin/env python3
"""
Test Google Calendar Authentication

Quick test to verify Google OAuth credentials work without creating calendar events.
"""

import os
from google_calendar_integration import GoogleCalendarTodoManager

def test_google_authentication():
    """Test Google Calendar and Tasks authentication"""
    
    print("🔐 Testing Google Calendar Authentication")
    print("=" * 50)
    
    # Initialize the calendar manager
    calendar_manager = GoogleCalendarTodoManager()
    
    # Try to authenticate
    print("🔧 Attempting to authenticate with Google...")
    
    if calendar_manager.authenticate():
        print("✅ Google authentication successful!")
        
        # Test calendar access
        print("\n📅 Testing calendar access...")
        calendars = calendar_manager.get_calendar_list()
        print(f"✅ Found {len(calendars)} calendars:")
        for cal in calendars[:3]:  # Show first 3
            print(f"  📅 {cal.get('summary', 'Unnamed Calendar')}")
        
        # Test tasks access
        print("\n✅ Testing Google Tasks access...")
        task_lists = calendar_manager.get_task_lists()
        print(f"✅ Found {len(task_lists)} task lists:")
        for tl in task_lists:
            print(f"  ✅ {tl.get('title', 'Unnamed Task List')}")
        
        print(f"\n🎉 Google integration is fully working!")
        print(f"📋 You can now create calendar events and tasks from your conversations!")
        
        return True
        
    else:
        print("❌ Google authentication failed!")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure credentials.json is in the current directory")
        print("2. Check that Google Calendar API is enabled")
        print("3. Verify OAuth consent screen is configured")
        print("4. Try running the main script again")
        
        return False

def test_single_todo():
    """Test creating a single calendar event"""
    
    print("\n🧪 Would you like to test creating ONE calendar event? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice != 'y':
        print("⏸️  Skipping test event creation")
        return
    
    calendar_manager = GoogleCalendarTodoManager()
    
    if not calendar_manager.authenticate():
        print("❌ Cannot test without authentication")
        return
    
    # Create a test todo
    test_todo = {
        'text': 'Test calendar integration from Limitless',
        'full_context': 'This is a test todo created to verify the integration works',
        'lifelog_id': 'test-123',
        'lifelog_title': 'Test Conversation',
        'source_time': '2024-01-01T12:00:00Z',
        'urgency': 'normal',
        'category': 'general',
        'extracted_at': '2024-01-01T12:00:00Z'
    }
    
    print("📅 Creating test calendar event...")
    event_id = calendar_manager.create_calendar_event(test_todo)
    
    if event_id:
        print("✅ Test calendar event created successfully!")
        print("📅 Check your Google Calendar for the test event")
    else:
        print("❌ Failed to create test event")
    
    print("\n✅ Creating test Google Task...")
    task_id = calendar_manager.create_google_task(test_todo)
    
    if task_id:
        print("✅ Test Google Task created successfully!")
        print("📝 Check Google Tasks (tasks.google.com) for the test task")
    else:
        print("❌ Failed to create test task")

if __name__ == "__main__":
    if test_google_authentication():
        test_single_todo()
    
    print(f"\n💡 Next steps:")
    print(f"- Run 'python3 limitless_todo_calendar.py' for full integration")
    print(f"- Run 'python3 claude_gentle_summary.py' for AI insights")
    print(f"- Your complete productivity system is ready! 🚀")


