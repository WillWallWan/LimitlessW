#!/usr/bin/env python3
"""
Check Available Google Calendars

Shows what calendars you have and lets you choose where to put conversation events.
"""

import os
from dotenv import load_dotenv
from google_calendar_integration import GoogleCalendarTodoManager

load_dotenv()

def show_available_calendars():
    """Show all available Google Calendars"""
    
    print("📅 Available Google Calendars")
    print("=" * 50)
    
    # Initialize Google Calendar manager
    calendar_manager = GoogleCalendarTodoManager()
    
    if not calendar_manager.authenticate():
        print("❌ Google Calendar authentication failed!")
        return
    
    print("✅ Connected to Google Calendar!")
    
    # Get list of calendars
    calendars = calendar_manager.get_calendar_list()
    
    if not calendars:
        print("❌ No calendars found")
        return
    
    print(f"\n📋 You have {len(calendars)} calendar(s):")
    print("-" * 40)
    
    for i, calendar in enumerate(calendars, 1):
        cal_id = calendar.get('id', 'Unknown')
        cal_name = calendar.get('summary', 'Unnamed Calendar')
        cal_description = calendar.get('description', '')
        is_primary = calendar.get('primary', False)
        access_role = calendar.get('accessRole', 'Unknown')
        
        # Color info
        color_id = calendar.get('colorId', '')
        background_color = calendar.get('backgroundColor', '')
        
        print(f"{i:2d}. {cal_name}")
        if is_primary:
            print(f"     🏠 PRIMARY CALENDAR")
        print(f"     📧 ID: {cal_id}")
        print(f"     🔑 Access: {access_role}")
        if cal_description:
            print(f"     📝 Description: {cal_description}")
        if background_color:
            print(f"     🎨 Color: {background_color}")
        print()
    
    print("💡 **Recommendations for Conversation Logs:**")
    print("-" * 50)
    print("1. 🆕 CREATE NEW: 'Conversations' calendar (cleanest)")
    print("2. 🏠 USE PRIMARY: Your main calendar (will be mixed with other events)")
    print("3. 📋 USE EXISTING: Choose from calendars above")
    
    print("\n🛠️ **Next Steps:**")
    print("- Choose where you want conversation events")
    print("- I can create a new calendar or use existing one")
    print("- Then we'll populate it with your conversation logs")

if __name__ == "__main__":
    show_available_calendars()


