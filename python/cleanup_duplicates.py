#!/usr/bin/env python3
"""
Clean up duplicate conversation events from Google Calendar
"""

from google_calendar_integration import GoogleCalendarTodoManager
from datetime import datetime, timedelta
from collections import defaultdict

def cleanup_duplicates():
    """Remove duplicate conversation events while keeping one copy"""
    
    print("🧹 Starting duplicate cleanup...")
    
    cal = GoogleCalendarTodoManager()
    if not cal.authenticate():
        print("❌ Failed to authenticate")
        return
    
    calendar_id = cal.get_or_create_conversations_calendar()
    
    # Check last 30 days
    total_removed = 0
    
    for days_ago in range(30):
        target_date = datetime.now().date() - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Query a wide range
        prev_day = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_day = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        events_result = cal.calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=f'{prev_day}T00:00:00Z',
            timeMax=f'{next_day}T23:59:59Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        all_events = events_result.get('items', [])
        
        # Filter to target date only
        events = []
        for event in all_events:
            event_start = event.get('start', {})
            if 'dateTime' in event_start:
                try:
                    event_dt = datetime.fromisoformat(event_start['dateTime'].replace('Z', '+00:00'))
                    if event_dt.date() == target_date:
                        events.append(event)
                except:
                    pass
        
        if not events:
            continue
        
        # Group by (title, start time) to find duplicates
        event_groups = defaultdict(list)
        for event in events:
            summary = event.get('summary', '')
            start = event.get('start', {}).get('dateTime', '')
            # Skip daily summaries
            if 'Daily Summary' in summary:
                continue
            key = (summary, start)
            event_groups[key].append(event)
        
        # Find and remove duplicates
        day_removed = 0
        for key, event_list in event_groups.items():
            if len(event_list) > 1:
                summary, start = key
                print(f"  {date_str}: '{summary[:50]}...' - {len(event_list)} copies found")
                # Keep the first one, delete the rest
                for event in event_list[1:]:
                    try:
                        cal.calendar_service.events().delete(
                            calendarId=calendar_id,
                            eventId=event['id']
                        ).execute()
                        day_removed += 1
                    except Exception as e:
                        print(f"    ⚠️  Failed to delete: {e}")
        
        if day_removed > 0:
            total_removed += day_removed
            print(f"  ✅ Removed {day_removed} duplicate(s) from {date_str}")
    
    print(f"\n✨ Cleanup complete! Removed {total_removed} total duplicates")

if __name__ == "__main__":
    cleanup_duplicates()









