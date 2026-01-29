#!/usr/bin/env python3
"""
Individual Conversation Logger for Limitless API + Google Calendar

This script:
1. Fetches all conversations from a specific day
2. Uses AI to individually summarize each conversation with rich context
3. Creates one calendar event per conversation
4. Provides complete, granular coverage of your day's conversations
"""

import os
import json
import time
import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
import anthropic
from _client import get_lifelogs
from google_calendar_integration import GoogleCalendarTodoManager

# Load environment variables
load_dotenv()

def get_individual_conversation_prompt(conversation_content, conversation_title):
    """Generate the AI prompt for individual conversation summarization"""
    return f"""Analyze this individual conversation and create a structured summary for a calendar event.

CONVERSATION CONTEXT:
- This is a single conversation from my day
- Title: {conversation_title}
- I want rich context so I can understand what happened without re-reading the transcript

Please provide a JSON response with the following fields:
- **description**: 2-3 sentence summary of what happened, key topics discussed, main activities
- **key_information**: Important information I learned or shared (if any, otherwise "None")
- **decisions_made**: Any decisions, commitments, or outcomes (if any, otherwise "None") 
- **problems_solutions**: Problems encountered and solutions discussed (if any, otherwise "None")
- **people_involved**: Names or descriptions of participants (if clear, otherwise "None")
- **conversation_type**: Category like "work", "social", "gaming", "planning", "personal", "transit", etc.

GUIDELINES:
- Include specific details, names, topics that provide full context
- Make each field clear and useful for calendar viewing
- If a field doesn't apply, use "None" rather than leaving it empty
- Focus on what I can learn from this summary about my day

CONVERSATION TRANSCRIPT:
{conversation_content}

Return ONLY valid JSON with the above fields:"""

def summarize_individual_conversation(conversation_content, conversation_title):
    """Use Claude to summarize an individual conversation"""
    
    # Initialize Claude client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env file")
        return None
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Generate the prompt
    prompt = get_individual_conversation_prompt(conversation_content, conversation_title)
    
    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            temperature=0.3,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        # Extract and parse the response
        response_text = message.content[0].text.strip()
        
        # Claude 4.5 often wraps JSON in markdown code blocks
        import re
        code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text, re.MULTILINE)
        if code_block_match:
            try:
                summary_data = json.loads(code_block_match.group(1))
                return summary_data
            except json.JSONDecodeError:
                pass
        
        # Try pure JSON parse
        try:
            summary_data = json.loads(response_text)
            return summary_data
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error for '{conversation_title}': {e}")
            # Return a basic structure if JSON parsing fails
            return {
                "description": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "key_information": "None",
                "decisions_made": "None", 
                "problems_solutions": "None",
                "people_involved": "None",
                "conversation_type": "general"
            }
        
    except Exception as e:
        print(f"❌ Error summarizing conversation '{conversation_title}': {e}")
        return None

def create_individual_calendar_event(lifelog, summary, calendar_manager, calendar_id):
    """Create a calendar event for an individual conversation"""
    
    try:
        title = lifelog.get('title', 'Conversation')
        start_time = lifelog.get('startTime', '')
        end_time = lifelog.get('endTime', '')
        
        # Parse start and end times
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            print(f"⚠️ Invalid time format for '{title}', skipping...")
            return None
        
        # Build event description
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        
        # Use structured summary if available, otherwise use original title with note
        if summary and isinstance(summary, dict):
            description = summary.get('description', 'No description available')
            key_information = summary.get('key_information', 'None')
            decisions_made = summary.get('decisions_made', 'None') 
            problems_solutions = summary.get('problems_solutions', 'None')
            people_involved = summary.get('people_involved', 'None')
            conversation_type = summary.get('conversation_type', 'general')
            
            event_description = f"""📅 Conversation Summary
📊 Type: {conversation_type.title()}
⏱️ Duration: {duration_minutes:.1f} minutes

📝 What Happened:
{description}"""

            # Add optional sections if they contain meaningful content
            # Handle different response types (string, dict, list)
            def is_meaningful_content(content):
                if not content:
                    return False
                if isinstance(content, str):
                    return content.lower() not in ["none", "n/a", ""]
                elif isinstance(content, (dict, list)):
                    return bool(content)  # Non-empty dict/list is meaningful
                return bool(content)
            
            def format_content(content):
                if isinstance(content, str):
                    return content
                elif isinstance(content, dict):
                    # Format dictionary as readable text instead of JSON
                    formatted_items = []
                    for key, value in content.items():
                        # Capitalize and format the key nicely
                        formatted_key = key.replace('_', ' ').title()
                        if isinstance(value, list):
                            # Format list values with bullet points
                            list_items = "\n  ".join(f"• {item}" for item in value)
                            formatted_items.append(f"{formatted_key}:\n  {list_items}")
                        else:
                            formatted_items.append(f"• {formatted_key}: {value}")
                    return "\n".join(formatted_items)
                elif isinstance(content, list):
                    # Handle list of strings or list of dicts
                    formatted_items = []
                    for item in content:
                        if isinstance(item, dict):
                            # Format each dict item
                            dict_parts = [f"{k}: {v}" for k, v in item.items()]
                            formatted_items.append(f"• {', '.join(dict_parts)}")
                        else:
                            formatted_items.append(f"• {item}")
                    return "\n".join(formatted_items)
                return str(content)

            if is_meaningful_content(key_information):
                event_description += f"""

💡 Key Information:
{format_content(key_information)}"""

            if is_meaningful_content(decisions_made):
                event_description += f"""

✅ Decisions Made:
{format_content(decisions_made)}"""

            if is_meaningful_content(problems_solutions):
                event_description += f"""

🔧 Problems & Solutions:
{format_content(problems_solutions)}"""

            if is_meaningful_content(people_involved):
                event_description += f"""

👥 People Involved:
{format_content(people_involved)}"""

            event_description += f"""

🤖 Generated by Limitless Individual Conversation Logger
🔗 Lifelog ID: {lifelog.get('id', 'unknown')}"""
        
        else:
            event_description = f"""📅 Conversation Log
⏱️ Duration: {duration_minutes:.1f} minutes

📝 Original Title: {title}

Note: AI summary unavailable for this conversation.

🤖 Generated by Limitless Individual Conversation Logger
🔗 Lifelog ID: {lifelog.get('id', 'unknown')}"""
        
        # Create calendar event
        event = {
            'summary': title[:100],  # Limit title length for calendar
            'description': event_description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
            'colorId': '8',  # Light blue
            'transparency': 'transparent',
        }
        
        # Create the event
        event_result = calendar_manager.calendar_service.events().insert(
            calendarId=calendar_id, body=event).execute()
        
        event_time = start_dt.strftime('%H:%M')
        print(f"✅ Created: '{title[:50]}...' ({event_time})")
        return event_result.get('id')
        
    except Exception as e:
        print(f"❌ Failed to create event for '{title}': {e}")
        return None

def clear_existing_events(calendar_manager, calendar_id, target_date):
    """Clear existing events from the Conversations calendar for the target date"""
    try:
        # Get events for the specific date - query a wider range to catch all timezones
        date_str = target_date.strftime('%Y-%m-%d')
        # Query from previous day to next day to ensure we catch all events
        prev_day = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_day = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        time_min = f"{prev_day}T00:00:00Z"
        time_max = f"{next_day}T23:59:59Z"
        
        events_result = calendar_manager.calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        all_events = events_result.get('items', [])
        
        print(f"   🔍 Found {len(all_events)} total events in range, filtering to {date_str}...")
        
        # Filter to only events that actually occur on the target date
        events = []
        for event in all_events:
            event_start = event.get('start', {})
            # For timed events, check if the date part matches
            if 'dateTime' in event_start:
                try:
                    event_dt = datetime.fromisoformat(event_start['dateTime'].replace('Z', '+00:00'))
                    if event_dt.date() == target_date:
                        events.append(event)
                except Exception as e:
                    print(f"   ⚠️ Error parsing event date: {e}")
                    pass
            # For all-day events, check the date field
            elif 'date' in event_start:
                if event_start['date'] == date_str:
                    events.append(event)
        
        print(f"   📊 Filtered to {len(events)} events on {date_str}")
        
        if events:
            # Filter out daily summary events
            events_to_delete = []
            preserved_summaries = 0
            
            for event in events:
                # Check if this is a daily summary event
                summary = event.get('summary', '')
                is_all_day = 'date' in event.get('start', {})
                
                # Preserve daily summary events
                if 'Daily Summary' in summary and is_all_day:
                    preserved_summaries += 1
                else:
                    events_to_delete.append(event)
            
            if events_to_delete:
                print(f"🗑️ Clearing {len(events_to_delete)} existing events from {date_str}...")
                if preserved_summaries > 0:
                    print(f"   📅 Preserving {preserved_summaries} daily summary event(s)")
                    
                for event in events_to_delete:
                    try:
                        calendar_manager.calendar_service.events().delete(
                            calendarId=calendar_id,
                            eventId=event['id']
                        ).execute()
                    except Exception as e:
                        print(f"⚠️ Failed to delete event: {e}")
                print(f"✅ Cleared existing events")
            else:
                if preserved_summaries > 0:
                    print(f"ℹ️ Only daily summary found for {date_str}, preserving it")
                else:
                    print(f"ℹ️ No existing events found for {date_str}")
            
    except Exception as e:
        print(f"⚠️ Failed to clear existing events: {e}")

def get_existing_lifelog_ids(calendar_manager, calendar_id, target_date):
    """Get lifelog IDs that already have calendar events for the target date"""
    import re
    existing_ids = set()
    
    try:
        # Get events for the specific date - query a wider range to catch all timezones
        date_str = target_date.strftime('%Y-%m-%d')
        prev_day = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_day = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        time_min = f"{prev_day}T00:00:00Z"
        time_max = f"{next_day}T23:59:59Z"
        
        events_result = calendar_manager.calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        all_events = events_result.get('items', [])
        
        # Filter to only events that actually occur on the target date
        for event in all_events:
            event_start = event.get('start', {})
            event_date_matches = False
            
            # For timed events, check if the date part matches
            if 'dateTime' in event_start:
                try:
                    event_dt = datetime.fromisoformat(event_start['dateTime'].replace('Z', '+00:00'))
                    if event_dt.date() == target_date:
                        event_date_matches = True
                except:
                    pass
            # For all-day events, check the date field
            elif 'date' in event_start:
                if event_start['date'] == date_str:
                    event_date_matches = True
            
            if event_date_matches:
                # Extract lifelog ID from description
                description = event.get('description', '')
                match = re.search(r'🔗 Lifelog ID: ([a-zA-Z0-9_-]+)', description)
                if match:
                    existing_ids.add(match.group(1))
        
        return existing_ids
        
    except Exception as e:
        print(f"⚠️ Failed to get existing lifelog IDs: {e}")
        return set()

def parse_date_argument(date_arg):
    """Parse date argument - can be YYYY-MM-DD, negative number for days ago, or None for yesterday"""
    if date_arg is None:
        # Default to yesterday
        return datetime.now().date() - timedelta(days=1)
    
    # Check if it's a negative number (days ago)
    try:
        days_ago = int(date_arg)
        if days_ago <= 0:
            return datetime.now().date() + timedelta(days=days_ago)
        else:
            print(f"⚠️ Please use negative numbers for days ago (e.g., -3 for 3 days ago)")
            sys.exit(1)
    except ValueError:
        pass
    
    # Try to parse as YYYY-MM-DD
    try:
        return datetime.strptime(date_arg, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ Invalid date format: '{date_arg}'")
        print("📝 Use YYYY-MM-DD format (e.g., 2025-08-20) or negative number for days ago (e.g., -3)")
        sys.exit(1)

def log_individual_conversations(target_date):
    """Main function to create individual calendar events for each conversation"""
    
    # Get API key
    api_key = os.getenv('LIMITLESS_API_KEY')
    if not api_key:
        print("❌ LIMITLESS_API_KEY not found in .env file")
        return
    
    # Format date for display and API
    date_str = target_date.strftime('%Y-%m-%d')
    days_ago = (datetime.now().date() - target_date).days
    
    if days_ago == 0:
        date_description = "today"
    elif days_ago == 1:
        date_description = "yesterday"
    elif days_ago > 1:
        date_description = f"{days_ago} days ago"
    else:
        date_description = f"in {-days_ago} days (future date!)"
    
    print(f"📅 Processing individual conversations from {date_str} ({date_description})")
    
    # Fetch lifelogs from target date
    print(f"\n🔍 Fetching conversations from Limitless API...")
    lifelogs = get_lifelogs(
        api_key=api_key,
        date=date_str,
        includeMarkdown=True,
        limit=100  # Get more to ensure we capture the full day
    )
    
    if not lifelogs:
        print(f"❌ No conversations found for {date_str}")
        return
    
    print(f"📊 Found {len(lifelogs)} total conversations")
    
    # Filter meaningful conversations (>30 seconds for individual processing)
    meaningful_conversations = []
    for lifelog in lifelogs:
        start_time = lifelog.get('startTime', '')
        end_time = lifelog.get('endTime', '')
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_seconds = (end_dt - start_dt).total_seconds()
                
                if duration_seconds >= 30:  # At least 30 seconds for individual events
                    meaningful_conversations.append(lifelog)
            except:
                pass  # Skip if we can't parse times
    
    print(f"🎯 Processing {len(meaningful_conversations)} meaningful conversations (>30 seconds)")
    
    if not meaningful_conversations:
        print("❌ No meaningful conversations found")
        return
    
    # Set up Google Calendar
    print(f"\n📅 Setting up Google Calendar integration...")
    calendar_manager = GoogleCalendarTodoManager()
    if not calendar_manager.authenticate():
        print("❌ Failed to authenticate with Google Calendar")
        return
    
    # Get or create the Conversations calendar
    conversations_calendar_id = calendar_manager.get_or_create_conversations_calendar()
    if not conversations_calendar_id:
        print("❌ Failed to create/find Conversations calendar")
        return
    
    # Clear existing events for this date to avoid duplicates
    clear_existing_events(calendar_manager, conversations_calendar_id, target_date)
    
    # Process each conversation individually
    print(f"\n🤖 Processing each conversation with Claude for structured summaries...")
    print(f"⏳ This will take ~{len(meaningful_conversations) * 3} seconds due to API rate limits\n")
    
    created_count = 0
    failed_count = 0
    
    for i, lifelog in enumerate(meaningful_conversations, 1):
        title = lifelog.get('title', 'Untitled')
        markdown = lifelog.get('markdown', '')
        start_time = lifelog.get('startTime', '')
        
        # Show progress
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_dt.strftime('%H:%M')
            print(f"[{i:2d}/{len(meaningful_conversations)}] {time_str} - {title[:50]}...")
        except:
            print(f"[{i:2d}/{len(meaningful_conversations)}] {title[:50]}...")
        
        # Summarize the conversation with Claude
        summary = summarize_individual_conversation(markdown, title)
        
        # Create calendar event
        event_id = create_individual_calendar_event(
            lifelog, summary, calendar_manager, conversations_calendar_id
        )
        
        if event_id:
            created_count += 1
        else:
            failed_count += 1
        
        # Rate limiting: pause between API calls
        if i < len(meaningful_conversations):  # Don't sleep after the last one
            time.sleep(3)  # 3 second pause between conversations to avoid rate limits
    
    print(f"\n🎉 Processing complete!")
    print(f"✅ Successfully created {created_count} calendar events")
    if failed_count > 0:
        print(f"❌ Failed to create {failed_count} events")
    print(f"📅 Check your 'Conversations' calendar for the complete day view")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Log individual conversations from Limitless to Google Calendar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 individual_conversation_logger.py              # Process yesterday (default)
  python3 individual_conversation_logger.py 2025-08-20   # Process specific date
  python3 individual_conversation_logger.py -3           # Process 3 days ago
  python3 individual_conversation_logger.py -7           # Process a week ago
        """
    )
    
    parser.add_argument(
        'date',
        nargs='?',  # Optional argument
        default=None,
        help='Date to process: YYYY-MM-DD format or negative number for days ago (default: yesterday)'
    )
    
    args = parser.parse_args()
    
    # Parse the date argument
    target_date = parse_date_argument(args.date)
    
    # Run the main function
    log_individual_conversations(target_date)
