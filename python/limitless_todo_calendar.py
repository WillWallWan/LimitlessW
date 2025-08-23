#!/usr/bin/env python3
"""
Limitless Todo Calendar Integration

This script extracts action items from your Limitless conversations
and automatically creates Google Calendar events or Google Tasks.

Usage:
    1. Set LIMITLESS_API_KEY environment variable
    2. Set up Google Calendar API credentials (see README instructions)
    3. Run: python limitless_todo_calendar.py
"""

import os
import sys
from dotenv import load_dotenv
from todo_tracker import TodoExtractor, get_lifelogs
from google_calendar_integration import GoogleCalendarTodoManager

# Load environment variables from .env file
load_dotenv()

def main():
    """Main function to extract todos and create calendar events"""
    
    print("🚀 Limitless Todo Calendar Integration")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("❌ Please set LIMITLESS_API_KEY environment variable")
        print("   Get your API key from: https://limitless.ai/developers")
        print("   Then run: export LIMITLESS_API_KEY='your_key_here'")
        return
    
    # Step 1: Extract todos from conversations
    print("\n🔍 Step 1: Extracting todos from recent conversations...")
    
    try:
        # Get recent lifelogs
        lifelogs = get_lifelogs(
            api_key=api_key,
            limit=50,  # Adjust based on how much data you have
            direction="desc",
            includeMarkdown=True
        )
        
        print(f"📚 Found {len(lifelogs)} recent conversations")
        
        # Extract todos
        extractor = TodoExtractor()
        todos = extractor.extract_todos_from_lifelogs(lifelogs)
        
        print(f"📝 Extracted {len(todos)} potential action items")
        
        # Deduplicate
        unique_todos = extractor.deduplicate_todos(todos)
        
        print(f"✨ After deduplication: {len(unique_todos)} unique todos")
        
        if not unique_todos:
            print("📭 No todos found in your recent conversations!")
            print("   Try having some conversations with action items like:")
            print("   - 'I need to call the doctor'")
            print("   - 'I'll follow up on that project'")
            print("   - 'I should buy groceries'")
            return
        
        # Show preview of todos
        print("\n📋 Preview of extracted todos:")
        for i, todo in enumerate(unique_todos[:5], 1):
            print(f"  {i}. [{todo['urgency'].upper()}] {todo['text'][:50]}{'...' if len(todo['text']) > 50 else ''}")
        
        if len(unique_todos) > 5:
            print(f"  ... and {len(unique_todos) - 5} more")
        
    except Exception as e:
        print(f"❌ Failed to extract todos: {e}")
        return
    
    # Step 2: Ask user if they want to proceed
    print(f"\n📅 Step 2: Creating calendar events/tasks...")
    proceed = input(f"Create calendar items for {len(unique_todos)} todos? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("⏸️  Operation cancelled")
        return
    
    # Step 3: Authenticate with Google
    print("\n🔐 Step 3: Authenticating with Google Calendar...")
    
    calendar_manager = GoogleCalendarTodoManager()
    
    if not calendar_manager.authenticate():
        print("\n❌ Google authentication failed!")
        print("\n📋 Setup Instructions:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Calendar API and Google Tasks API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download the credentials file as 'credentials.json'")
        print("6. Place it in this directory")
        print("7. Run this script again")
        return
    
    # Step 4: Create calendar items
    print("\n🔧 Step 4: How would you like to create todos?")
    print("1. Calendar events (with time blocks)")
    print("2. Google Tasks (task list)")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice not in ['1', '2', '3']:
        print("❌ Invalid choice. Exiting.")
        return
    
    print(f"\n⚡ Creating calendar items...")
    
    created_events = 0
    created_tasks = 0
    
    # Process each todo
    for i, todo in enumerate(unique_todos, 1):
        print(f"Processing {i}/{len(unique_todos)}: {todo['text'][:40]}{'...' if len(todo['text']) > 40 else ''}")
        
        if choice in ['1', '3']:
            # Create calendar event
            event_id = calendar_manager.create_calendar_event(todo)
            if event_id:
                created_events += 1
        
        if choice in ['2', '3']:
            # Create Google Task
            task_id = calendar_manager.create_google_task(todo)
            if task_id:
                created_tasks += 1
    
    # Step 5: Summary
    print(f"\n🎉 Todo Calendar Integration Complete!")
    print("=" * 50)
    print(f"📊 Summary:")
    print(f"  • Conversations analyzed: {len(lifelogs)}")
    print(f"  • Todos extracted: {len(unique_todos)}")
    print(f"  • Calendar events created: {created_events}")
    print(f"  • Google Tasks created: {created_tasks}")
    
    if choice in ['1', '3'] and created_events > 0:
        print(f"\n📅 Check your Google Calendar for the new events!")
    
    if choice in ['2', '3'] and created_tasks > 0:
        print(f"\n✅ Check Google Tasks (tasks.google.com) for your new tasks!")
    
    print(f"\n💡 Tip: Run this script regularly to stay on top of your action items!")

if __name__ == "__main__":
    main()
