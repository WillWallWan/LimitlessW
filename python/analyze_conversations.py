#!/usr/bin/env python3
"""
Analyze Conversation Patterns

Shows timestamps, frequency, and daily patterns of your Limitless conversations.
"""

import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def analyze_conversation_timing():
    """Analyze the timing and frequency of conversations"""
    
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print("🔍 Analyzing Your Conversation Patterns")
    print("=" * 60)
    
    # Get a larger sample to analyze patterns
    print("📚 Fetching conversations for analysis...")
    lifelogs = get_lifelogs(
        api_key=api_key,
        limit=100,  # Get more data for better analysis
        direction="desc",
        includeMarkdown=True
    )
    
    if not lifelogs:
        print("📭 No conversations found!")
        return
    
    print(f"✅ Analyzing {len(lifelogs)} conversations\n")
    
    # Parse timestamps and analyze patterns
    conversations_by_date = defaultdict(list)
    conversations_by_hour = defaultdict(int)
    conversation_durations = []
    
    print("📅 **Recent Conversations:**")
    print("-" * 60)
    
    for i, lifelog in enumerate(lifelogs[:10], 1):  # Show first 10
        title = lifelog.get('title', 'Untitled')
        start_time = lifelog.get('startTime', 'Unknown')
        end_time = lifelog.get('endTime', 'Unknown')
        
        print(f"{i:2d}. {title[:50]}")
        print(f"    🕐 Start: {start_time}")
        print(f"    🕐 End:   {end_time}")
        
        # Calculate duration if both times available
        if start_time != 'Unknown' and end_time != 'Unknown':
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                print(f"    ⏱️  Duration: {duration}")
                conversation_durations.append(duration.total_seconds() / 60)  # minutes
                
                # Group by date
                date_key = start_dt.date()
                conversations_by_date[date_key].append(lifelog)
                
                # Group by hour
                hour_key = start_dt.hour
                conversations_by_hour[hour_key] += 1
                
            except Exception as e:
                print(f"    ⚠️  Could not parse time: {e}")
        
        print()
    
    if len(lifelogs) > 10:
        print(f"... and {len(lifelogs) - 10} more conversations")
    
    # Daily conversation analysis
    print("\n📊 **Daily Conversation Patterns:**")
    print("-" * 60)
    
    if conversations_by_date:
        # Sort dates
        sorted_dates = sorted(conversations_by_date.keys(), reverse=True)
        
        print("Recent days:")
        for date in sorted_dates[:7]:  # Last 7 days
            count = len(conversations_by_date[date])
            total_duration = 0
            
            for conv in conversations_by_date[date]:
                start_time = conv.get('startTime', '')
                end_time = conv.get('endTime', '')
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        duration = end_dt - start_dt
                        total_duration += duration.total_seconds() / 60
                    except:
                        pass
            
            print(f"📅 {date}: {count:2d} conversations, {total_duration:.1f} minutes total")
        
        # Calculate averages
        daily_counts = [len(conversations_by_date[date]) for date in conversations_by_date]
        avg_daily = sum(daily_counts) / len(daily_counts) if daily_counts else 0
        max_daily = max(daily_counts) if daily_counts else 0
        min_daily = min(daily_counts) if daily_counts else 0
        
        print(f"\n📈 **Daily Statistics:**")
        print(f"   Average conversations per day: {avg_daily:.1f}")
        print(f"   Maximum conversations in a day: {max_daily}")
        print(f"   Minimum conversations in a day: {min_daily}")
        
    # Hourly patterns
    print(f"\n🕐 **Hourly Conversation Patterns:**")
    print("-" * 60)
    
    if conversations_by_hour:
        # Show busiest hours
        sorted_hours = sorted(conversations_by_hour.items(), key=lambda x: x[1], reverse=True)
        
        print("Most active hours:")
        for hour, count in sorted_hours[:8]:  # Top 8 hours
            # Convert to 12-hour format
            if hour == 0:
                hour_str = "12:00 AM"
            elif hour < 12:
                hour_str = f"{hour}:00 AM"
            elif hour == 12:
                hour_str = "12:00 PM"
            else:
                hour_str = f"{hour-12}:00 PM"
            
            # Create a simple bar chart
            bar = "█" * (count // 2) + ("▌" if count % 2 else "")
            print(f"   {hour_str:8s} │{bar} {count}")
    
    # Duration analysis
    if conversation_durations:
        avg_duration = sum(conversation_durations) / len(conversation_durations)
        max_duration = max(conversation_durations)
        min_duration = min(conversation_durations)
        
        print(f"\n⏱️  **Conversation Duration Analysis:**")
        print("-" * 60)
        print(f"   Average duration: {avg_duration:.1f} minutes")
        print(f"   Longest conversation: {max_duration:.1f} minutes")
        print(f"   Shortest conversation: {min_duration:.1f} minutes")
    
    print(f"\n💡 **Insights for Todo Extraction:**")
    print("-" * 60)
    if conversations_by_date:
        recent_days = len([d for d in conversations_by_date.keys() 
                          if d >= datetime.now().date() - timedelta(days=7)])
        print(f"   • You have data from {len(conversations_by_date)} different days")
        print(f"   • {recent_days} days in the last week have conversations")
        
        if avg_daily > 0:
            days_for_50_convos = 50 / avg_daily
            print(f"   • 50 conversations covers ~{days_for_50_convos:.1f} days of your data")
            
            if days_for_50_convos > 7:
                print(f"   • Consider limit=20 for recent focus (weekly)")
            elif days_for_50_convos > 3:
                print(f"   • Current limit=50 gives good weekly+ coverage")
            else:
                print(f"   • Consider limit=100+ for broader analysis")

def show_sample_conversation_structure():
    """Show the exact structure of a conversation"""
    
    api_key = os.getenv("LIMITLESS_API_KEY")
    if not api_key:
        return
    
    print(f"\n🔬 **Sample Conversation Structure:**")
    print("-" * 60)
    
    # Get just one conversation to examine
    lifelogs = get_lifelogs(
        api_key=api_key,
        limit=1,
        direction="desc",
        includeMarkdown=True
    )
    
    if lifelogs:
        lifelog = lifelogs[0]
        
        print("📋 Available fields in each conversation:")
        for key, value in lifelog.items():
            if key == 'markdown' and value:
                # Truncate markdown for display
                truncated = value[:200] + "..." if len(value) > 200 else value
                print(f"   {key:15s}: {truncated}")
            else:
                print(f"   {key:15s}: {value}")

if __name__ == "__main__":
    analyze_conversation_timing()
    show_sample_conversation_structure()


