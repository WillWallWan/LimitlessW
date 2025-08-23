#!/usr/bin/env python3
"""
Intelligent Day Logger for Limitless API + Google Calendar

This script:
1. Fetches all conversations from a specific day
2. Uses AI to intelligently group them into meaningful periods
3. Creates calendar events for each grouped conversation period
4. Provides a clean, organized view of your day's conversations
"""

import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import anthropic
from _client import get_lifelogs
from google_calendar_integration import GoogleCalendarTodoManager

# Load environment variables
load_dotenv()

def get_day_grouping_prompt(all_conversations_content):
    """Generate the AI prompt for intelligent conversation grouping"""
    return f"""Analyze these conversation transcripts from my day and group them into meaningful conversation periods that would be useful as calendar events.

INSTRUCTIONS:
1. **Group conversations** that are close in time (within 15-30 minutes) and/or thematically related
2. **Create natural periods** but be more granular - capture most of the day's meaningful activity
3. **Skip only very brief** conversations (under 30 seconds of substantive content)
4. **Identify the overall theme/purpose** of each grouped period with rich context
5. **Set realistic time spans** based on when conversations actually occurred

For each meaningful conversation period, provide:
- **title**: Descriptive, calendar-friendly title (e.g., "Morning project planning calls with team")
- **description**: Comprehensive summary covering what was discussed, decisions made, information learned, problems encountered, and solutions found. Include specific details, names, topics, and outcomes that provide full context.
- **start_time**: Earliest conversation time in this period (YYYY-MM-DD HH:MM format)
- **end_time**: Latest conversation time in this period (YYYY-MM-DD HH:MM format)
- **key_topics**: Main themes/subjects covered
- **type**: Category like "work", "social", "gaming", "planning", "personal"
- **key_information**: Important information learned or shared
- **decisions_made**: Any decisions or commitments that emerged
- **problems_solutions**: Problems encountered and solutions discussed

GROUPING GUIDELINES:
- Conversations within 15-30 minutes → likely same period
- Time gaps of 1+ hours → usually separate periods  
- Different contexts (work vs personal) → separate periods
- **CRITICAL: Capture ALL substantial conversations (>60 seconds) - do not skip time periods**
- **CRITICAL: If there are conversations throughout the day, there should be NO large time gaps (>2 hours) without coverage**
- Err on the side of more periods rather than fewer - provide comprehensive day coverage
- Include routine/casual conversations if they fill time gaps - these are part of daily life

Return ONLY a JSON array of conversation periods with NO extra text, comments, or explanations:

Conversation transcripts:
{all_conversations_content}

CRITICAL: Return ONLY valid JSON array. NO text before or after the JSON:"""

def prepare_conversations_for_ai(lifelogs):
    """Prepare conversation data for AI analysis"""
    conversations_text = ""
    
    for i, lifelog in enumerate(lifelogs):
        start_time = lifelog.get('startTime', '')
        title = lifelog.get('title', 'Untitled')
        markdown = lifelog.get('markdown', '')
        
        # Parse start time for display
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_dt.strftime('%H:%M')
        except:
            time_str = start_time
        
        conversations_text += f"""
=== CONVERSATION {i+1} ===
Time: {time_str}
Title: {title}
Content:
{markdown[:1000]}{'...' if len(markdown) > 1000 else ''}

"""
    
    return conversations_text

def detect_time_gaps(conversation_periods, lifelogs):
    """Detect large time gaps in conversation coverage and report missing periods"""
    
    if not conversation_periods:
        return []
    
    # Create timeline of covered periods
    covered_periods = []
    for period in conversation_periods:
        start_time = period.get('start_time', '')
        end_time = period.get('end_time', '')
        try:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
            covered_periods.append((start_dt, end_dt, period.get('title', '')))
        except:
            continue
    
    # Sort by start time
    covered_periods.sort(key=lambda x: x[0])
    
    # Find conversations in large gaps (>2 hours)
    gaps = []
    for i in range(len(covered_periods) - 1):
        current_end = covered_periods[i][1]
        next_start = covered_periods[i + 1][0]
        gap_duration = (next_start - current_end).total_seconds() / 3600  # hours
        
        if gap_duration > 2:  # Gap > 2 hours
            print(f"⚠️ LARGE GAP DETECTED: {current_end.strftime('%H:%M')} to {next_start.strftime('%H:%M')} ({gap_duration:.1f} hours)")
            
            # Find conversations in this gap
            gap_conversations = []
            for lifelog in lifelogs:
                start_time = lifelog.get('startTime', '')
                try:
                    conv_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    # Only check if conversation starts in the gap (ignore end time)
                    if current_end < conv_start < next_start:
                        gap_conversations.append(lifelog)
                except:
                    continue
            
            if gap_conversations:
                print(f"📋 Found {len(gap_conversations)} conversations in this gap!")
                gaps.append({
                    'start': current_end,
                    'end': next_start,
                    'conversations': gap_conversations
                })
    
    return gaps

def group_conversations_with_ai(lifelogs):
    """Use Claude to intelligently group conversations into periods"""
    
    # Initialize Claude client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env file")
        return []
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Prepare conversation data
    conversations_content = prepare_conversations_for_ai(lifelogs)
    
    print(f"🤖 Analyzing {len(lifelogs)} conversations with Claude...")
    print(f"📊 Total content length: {len(conversations_content):,} characters")
    
    # Generate conversation timeline for Claude
    timeline_summary = "\n=== CONVERSATION TIMELINE OVERVIEW ===\n"
    for i, lifelog in enumerate(lifelogs):
        start_time = lifelog.get('startTime', '')
        title = lifelog.get('title', 'Untitled')
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_dt.strftime('%H:%M')
            timeline_summary += f"{time_str} - {title[:60]}...\n"
        except:
            timeline_summary += f"{start_time} - {title[:60]}...\n"
    timeline_summary += "=== END TIMELINE ===\n\n"
    
    # Generate the prompt with timeline
    prompt = get_day_grouping_prompt(timeline_summary + conversations_content)
    
    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
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
        print(f"🧠 Claude response preview: {response_text[:200]}...")
        
        # Try to parse as JSON
        try:
            parsed_response = json.loads(response_text)
            
            # Handle different response formats
            if isinstance(parsed_response, list):
                conversation_periods = parsed_response
            elif isinstance(parsed_response, dict) and 'conversation_periods' in parsed_response:
                conversation_periods = parsed_response['conversation_periods']
            else:
                print(f"❌ Unexpected response format: {type(parsed_response)}")
                print(f"Raw response: {response_text}")
                return []
            
            print(f"✅ Successfully parsed {len(conversation_periods)} conversation periods")
            return conversation_periods
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Raw response: {response_text}")
            return []
            
    except Exception as e:
        print(f"❌ Error calling Claude API: {e}")
        return []

def clear_existing_events(calendar_manager, calendar_id, target_date):
    """Clear existing events from the Conversations calendar for the target date"""
    try:
        # Get events for the specific date
        date_str = target_date.strftime('%Y-%m-%d')
        time_min = f"{date_str}T00:00:00Z"
        time_max = f"{date_str}T23:59:59Z"
        
        events_result = calendar_manager.calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if events:
            print(f"🗑️ Clearing {len(events)} existing events from {date_str}...")
            for event in events:
                try:
                    calendar_manager.calendar_service.events().delete(
                        calendarId=calendar_id,
                        eventId=event['id']
                    ).execute()
                except Exception as e:
                    print(f"⚠️ Failed to delete event: {e}")
            print(f"✅ Cleared existing events")
        else:
            print(f"ℹ️ No existing events found for {date_str}")
            
    except Exception as e:
        print(f"⚠️ Failed to clear existing events: {e}")

def create_grouped_calendar_events(conversation_periods, calendar_manager, calendar_id):
    """Create calendar events for each grouped conversation period"""
    
    created_count = 0
    
    for period in conversation_periods:
        try:
            title = period.get('title', 'Conversation Period')
            description = period.get('description', '')
            start_time = period.get('start_time', '')
            end_time = period.get('end_time', '')
            key_topics = period.get('key_topics', [])
            period_type = period.get('type', 'general')
            key_information = period.get('key_information', '')
            decisions_made = period.get('decisions_made', '')
            problems_solutions = period.get('problems_solutions', '')
            
            # Parse start and end times
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
            except ValueError:
                print(f"⚠️ Invalid time format for '{title}', skipping...")
                continue
            
            # Build event description
            topics_str = ", ".join(key_topics) if key_topics else "Various topics"
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
            
            event_description = f"""📅 Conversation Period Summary
📊 Type: {period_type.title()}
⏱️ Duration: {duration_minutes:.0f} minutes
🏷️ Topics: {topics_str}

📝 What Happened:
{description}"""

            # Add optional sections if they exist
            if key_information:
                event_description += f"""

💡 Key Information:
{key_information}"""

            if decisions_made:
                event_description += f"""

✅ Decisions Made:
{decisions_made}"""

            if problems_solutions:
                event_description += f"""

🔧 Problems & Solutions:
{problems_solutions}"""

            event_description += f"""

🤖 Generated by Limitless Intelligent Day Logger"""
            
            # Create calendar event
            event = {
                'summary': title,
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
            
            print(f"✅ Created: '{title}' ({start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')})")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Failed to create event for '{title}': {e}")
    
    return created_count

def log_intelligent_day():
    """Main function to analyze and log a day's conversations intelligently"""
    
    # Get API key
    api_key = os.getenv('LIMITLESS_API_KEY')
    if not api_key:
        print("❌ LIMITLESS_API_KEY not found in .env file")
        return
    
    # Calculate yesterday's date
    yesterday = (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"📅 Analyzing conversations from {yesterday}")
    
    # Fetch lifelogs from yesterday
    print(f"\n🔍 Fetching conversations from Limitless API...")
    lifelogs = get_lifelogs(
        api_key=api_key,
        date=yesterday,
        includeMarkdown=True,
        limit=100  # Get more to ensure we capture the full day
    )
    
    if not lifelogs:
        print("❌ No conversations found for yesterday")
        return
    
    print(f"📊 Found {len(lifelogs)} conversations")
    
    # Filter meaningful conversations (>15 seconds - be more inclusive)
    meaningful_conversations = []
    for lifelog in lifelogs:
        start_time = lifelog.get('startTime', '')
        end_time = lifelog.get('endTime', '')
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_seconds = (end_dt - start_dt).total_seconds()
                
                if duration_seconds >= 15:  # At least 15 seconds - more inclusive
                    meaningful_conversations.append(lifelog)
            except:
                pass  # Skip if we can't parse times
    
    print(f"🎯 Found {len(meaningful_conversations)} meaningful conversations (>15 seconds)")
    
    if not meaningful_conversations:
        print("❌ No meaningful conversations found")
        return
    
    # Group conversations with AI
    print(f"\n🤖 Using AI to group conversations into periods...")
    conversation_periods = group_conversations_with_ai(meaningful_conversations)
    
    if not conversation_periods:
        print("❌ Failed to group conversations")
        return
    
    print(f"📅 AI identified {len(conversation_periods)} conversation periods:")
    for i, period in enumerate(conversation_periods, 1):
        title = period.get('title', 'Untitled')
        start_time = period.get('start_time', '')
        end_time = period.get('end_time', '')
        print(f"  {i}. {title} ({start_time} - {end_time})")
    
    # Check for large time gaps
    print(f"\n🔍 Checking for time gaps...")
    gaps = detect_time_gaps(conversation_periods, meaningful_conversations)
    if gaps:
        print(f"⚠️ WARNING: Found {len(gaps)} large time gaps in coverage!")
        print(f"📊 This suggests {sum(len(gap['conversations']) for gap in gaps)} conversations were missed by AI grouping")
    else:
        print(f"✅ No significant time gaps detected")
    
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
    yesterday_date = datetime.now().date() - timedelta(days=1)
    clear_existing_events(calendar_manager, conversations_calendar_id, yesterday_date)
    
    # Create calendar events for grouped periods
    print(f"\n📝 Creating calendar events for conversation periods...")
    created_count = create_grouped_calendar_events(
        conversation_periods, 
        calendar_manager, 
        conversations_calendar_id
    )
    
    print(f"\n🎉 Successfully created {created_count} calendar events!")
    print(f"📅 Check your 'Conversations' calendar to see the organized day view")

if __name__ == "__main__":
    log_intelligent_day()
