#!/usr/bin/env python3
"""
Daily Summary Calendar Event Creator

Creates comprehensive all-day calendar events that summarize entire days of conversations.
Can be used standalone or integrated with batch processing.
"""

import os
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from dotenv import load_dotenv
import anthropic
from google_calendar_integration import GoogleCalendarTodoManager

# Load environment variables
load_dotenv()

def get_daily_summary_prompt(conversations: List[Dict], date_str: str) -> str:
    """Generate prompt for comprehensive daily summary"""
    
    # Build conversation text with times
    conv_text = ""
    for conv in conversations:
        title = conv.get('title', 'Untitled')
        start_time = conv.get('startTime', '')
        markdown = conv.get('markdown', '')
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_dt.strftime('%I:%M %p')
        except:
            time_str = "Unknown time"
        
        conv_text += f"\n[{time_str}] {title}\n{markdown[:500]}...\n"
    
    return f"""Create a comprehensive daily summary for {date_str} based on these conversations.

CONVERSATIONS:
{conv_text}

Please provide a JSON response with the following structure:
{{
    "executive_summary": "2-3 sentence overview of the entire day",
    "key_themes": ["theme1", "theme2", "theme3"],
    "major_accomplishments": ["accomplishment1", "accomplishment2"],
    "important_decisions": ["decision1", "decision2"],
    "notable_interactions": ["person1: context", "person2: context"],
    "action_items": ["action1", "action2"],
    "insights_learned": ["insight1", "insight2"],
    "emotional_tone": "Overall emotional tone of the day",
    "productivity_score": "High/Medium/Low with brief explanation",
    "memorable_moments": ["moment1", "moment2"]
}}

Focus on:
- Identifying patterns across conversations
- Highlighting the most important events
- Providing actionable insights
- Creating a narrative of the day

Return ONLY valid JSON:"""

def create_daily_summary(conversations: List[Dict], target_date: date) -> Optional[Dict]:
    """Generate AI summary for an entire day's conversations"""
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found")
        return None
    
    client = anthropic.Anthropic(api_key=api_key)
    date_str = target_date.strftime('%Y-%m-%d')
    
    # Generate prompt
    prompt = get_daily_summary_prompt(conversations, date_str)
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
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
        except json.JSONDecodeError:
            print(f"⚠️ Failed to parse AI response for {date_str}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating daily summary: {e}")
        return None

def format_daily_summary(summary: Dict, stats: Dict) -> str:
    """Format the daily summary for calendar event description"""
    
    description = f"""📊 DAILY OVERVIEW
═══════════════════════════════════

📝 Executive Summary:
{summary.get('executive_summary', 'No summary available')}

🎯 Key Themes:
{chr(10).join(f'• {theme}' for theme in summary.get('key_themes', []))}

✅ Major Accomplishments:
{chr(10).join(f'• {acc}' for acc in summary.get('major_accomplishments', [])) or '• None recorded'}

💡 Important Decisions:
{chr(10).join(f'• {dec}' for dec in summary.get('important_decisions', [])) or '• None recorded'}

👥 Notable Interactions:
{chr(10).join(f'• {person}' for person in summary.get('notable_interactions', [])) or '• None recorded'}

📋 Action Items:
{chr(10).join(f'☐ {item}' for item in summary.get('action_items', [])) or '• None identified'}

🧠 Insights Learned:
{chr(10).join(f'• {insight}' for insight in summary.get('insights_learned', [])) or '• None captured'}

🎭 Emotional Tone: {summary.get('emotional_tone', 'Neutral')}
⚡ Productivity: {summary.get('productivity_score', 'Not assessed')}

✨ Memorable Moments:
{chr(10).join(f'• {moment}' for moment in summary.get('memorable_moments', [])) or '• None highlighted'}

───────────────────────────────────
📈 Day Statistics:
• Total Conversations: {stats.get('total_conversations', 0)}
• Total Duration: {stats.get('total_duration', 0):.1f} minutes
• Most Active Period: {stats.get('most_active_period', 'N/A')}
• Longest Conversation: {stats.get('longest_conversation', 'N/A')}

🤖 Generated by Limitless Daily Summary
"""
    return description

def calculate_day_stats(conversations: List[Dict]) -> Dict:
    """Calculate statistics for the day"""
    stats = {
        'total_conversations': len(conversations),
        'total_duration': 0,
        'most_active_period': 'Morning',
        'longest_conversation': None,
        'conversation_times': []
    }
    
    max_duration = 0
    hour_counts = {}
    
    for conv in conversations:
        try:
            start = datetime.fromisoformat(conv.get('startTime', '').replace('Z', '+00:00'))
            end = datetime.fromisoformat(conv.get('endTime', '').replace('Z', '+00:00'))
            duration = (end - start).total_seconds() / 60
            
            stats['total_duration'] += duration
            
            # Track longest conversation
            if duration > max_duration:
                max_duration = duration
                stats['longest_conversation'] = f"{conv.get('title', 'Untitled')} ({duration:.0f}m)"
            
            # Track activity by hour
            hour = start.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
        except:
            pass
    
    # Determine most active period
    if hour_counts:
        peak_hour = max(hour_counts, key=hour_counts.get)
        if peak_hour < 12:
            stats['most_active_period'] = 'Morning'
        elif peak_hour < 17:
            stats['most_active_period'] = 'Afternoon'
        else:
            stats['most_active_period'] = 'Evening'
    
    return stats

def create_allday_calendar_event(
    summary_data: Dict,
    stats: Dict,
    target_date: date,
    calendar_manager: GoogleCalendarTodoManager,
    calendar_id: str
) -> Optional[str]:
    """Create an all-day calendar event with the daily summary"""
    
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        day_name = target_date.strftime('%A')
        
        # Create event title with emoji based on productivity
        productivity = summary_data.get('productivity_score', '')
        if 'High' in productivity:
            emoji = "🚀"
        elif 'Medium' in productivity:
            emoji = "✅"
        else:
            emoji = "📅"
        
        event_title = f"{emoji} Daily Summary - {day_name} ({stats['total_conversations']} conversations)"
        
        # Format the description
        description = format_daily_summary(summary_data, stats)
        
        # Create all-day event
        event = {
            'summary': event_title,
            'description': description,
            'start': {
                'date': date_str,
            },
            'end': {
                'date': date_str,
            },
            'colorId': '9',  # Bold blue for daily summaries
            'transparency': 'transparent',
        }
        
        # Create the event
        event_result = calendar_manager.calendar_service.events().insert(
            calendarId=calendar_id, body=event
        ).execute()
        
        print(f"📅 Created daily summary for {date_str}")
        return event_result.get('id')
        
    except Exception as e:
        print(f"❌ Failed to create daily summary event: {e}")
        return None

def process_day_summary(
    conversations: List[Dict],
    target_date: date,
    calendar_manager: GoogleCalendarTodoManager,
    calendar_id: str
) -> bool:
    """Process and create a daily summary for a given day"""
    
    if not conversations:
        print(f"⚠️ No conversations to summarize for {target_date}")
        return False
    
    # Calculate statistics
    stats = calculate_day_stats(conversations)
    
    # Generate AI summary
    print(f"🤖 Generating AI summary for {target_date}...")
    summary_data = create_daily_summary(conversations, target_date)
    
    if not summary_data:
        print(f"❌ Failed to generate summary for {target_date}")
        return False
    
    # Create calendar event
    event_id = create_allday_calendar_event(
        summary_data, stats, target_date, calendar_manager, calendar_id
    )
    
    return event_id is not None

def clear_existing_daily_summary(
    calendar_manager: GoogleCalendarTodoManager,
    calendar_id: str,
    target_date: date
) -> None:
    """Remove any existing daily summary events for a given date"""
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        
        # For all-day events, we need to query a wider range and filter by date
        # Query the entire day plus a buffer
        prev_day = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_day = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        events_result = calendar_manager.calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=f"{prev_day}T00:00:00Z",
            timeMax=f"{next_day}T23:59:59Z",
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        removed_count = 0
        
        for event in events:
            # Check if it's a daily summary all-day event for our target date
            event_start = event.get('start', {})
            if 'date' in event_start and event_start['date'] == date_str:
                summary = event.get('summary', '')
                if 'Daily Summary' in summary:
                    try:
                        calendar_manager.calendar_service.events().delete(
                            calendarId=calendar_id,
                            eventId=event['id']
                        ).execute()
                        removed_count += 1
                    except:
                        pass
        
        if removed_count > 0:
            print(f"   🗑️ Removed {removed_count} existing daily summary event(s) for {date_str}")
        else:
            print(f"   ℹ️ No existing daily summary to clear for {date_str}")
                    
    except Exception as e:
        print(f"⚠️ Error clearing daily summaries: {e}")

if __name__ == "__main__":
    # Example usage - this would typically be called from batch_conversation_logger
    print("📊 Daily Summary Calendar Event Creator")
    print("This module is designed to be imported by batch_conversation_logger.py")
    print("\nTo use daily summaries, run:")
    print("python3 batch_conversation_logger.py --last 7 --daily-summary")
