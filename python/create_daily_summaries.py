#!/usr/bin/env python3
"""
Standalone Daily Summary Creator

Creates all-day summary events for dates that already have individual conversation events.
This is a thin wrapper around the core daily_summary_calendar logic.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, date
from typing import List
from dotenv import load_dotenv
from _client import get_lifelogs
from google_calendar_integration import GoogleCalendarTodoManager
from daily_summary_calendar import (
    process_day_summary,
    clear_existing_daily_summary
)
from batch_conversation_logger import EnhancedBatchLogger

# Load environment variables
load_dotenv()

def create_summaries_for_dates(dates: List[date], skip_existing: bool = True):
    """Create daily summaries for specified dates - reuses batch logger logic"""
    
    # Initialize the batch logger (we'll use its initialization logic)
    logger = EnhancedBatchLogger(create_daily_summaries=False)  # We'll handle summaries manually
    if not logger.initialize():
        return False
    
    print(f"\n🚀 Creating daily summaries for {len(dates)} day(s)")
    print("=" * 60)
    
    successful_summaries = 0
    failed_summaries = 0
    
    for target_date in sorted(dates):
        date_str = target_date.strftime('%Y-%m-%d')
        days_ago = (datetime.now().date() - target_date).days
        
        # Format date description
        if days_ago == 0:
            date_desc = "today"
        elif days_ago == 1:
            date_desc = "yesterday"
        elif days_ago > 1:
            date_desc = f"{days_ago} days ago"
        else:
            date_desc = f"in {-days_ago} days"
        
        print(f"\n📆 Processing {date_str} ({date_desc})")
        print("-" * 40)
        
        # Check if daily summary already exists (if skip_existing is True)
        if skip_existing:
            try:
                # Search for existing daily summary
                events_result = logger.calendar_manager.calendar_service.events().list(
                    calendarId=logger.conversations_calendar_id,
                    timeMin=f"{date_str}T00:00:00Z",
                    timeMax=f"{date_str}T23:59:59Z",
                    q="Daily Summary",
                    singleEvents=True
                ).execute()
                
                events = events_result.get('items', [])
                has_summary = any('date' in event.get('start', {}) for event in events)
                
                if has_summary:
                    print("   ⏭️ Skipping - daily summary already exists")
                    continue
            except:
                pass
        
        # Fetch conversations from Limitless
        print("   🔍 Fetching conversations from Limitless...")
        lifelogs = get_lifelogs(
            api_key=logger.api_key,
            date=date_str,
            includeMarkdown=True,
            limit=100
        )
        
        if not lifelogs:
            print("   ⚪ No conversations found")
            continue
        
        # Filter meaningful conversations (>30 seconds) - reuse batch logger's logic
        meaningful_conversations = []
        for lifelog in lifelogs:
            start_time = lifelog.get('startTime', '')
            end_time = lifelog.get('endTime', '')
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    
                    if duration_seconds >= 30:
                        meaningful_conversations.append(lifelog)
                except:
                    pass
        
        if not meaningful_conversations:
            print(f"   🟡 Found {len(lifelogs)} conversations but none >30 seconds")
            continue
        
        print(f"   📊 Found {len(meaningful_conversations)} meaningful conversations")
        
        # Clear any existing daily summary (in case we're updating)
        if not skip_existing:
            clear_existing_daily_summary(logger.calendar_manager, logger.conversations_calendar_id, target_date)
        
        # Create the daily summary using the shared function
        print("   🤖 Generating AI summary...")
        if process_day_summary(
            meaningful_conversations,
            target_date,
            logger.calendar_manager,
            logger.conversations_calendar_id
        ):
            print("   ✅ Daily summary created successfully")
            successful_summaries += 1
        else:
            print("   ❌ Failed to create daily summary")
            failed_summaries += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY CREATION COMPLETE")
    print("=" * 60)
    print(f"✅ Successful: {successful_summaries} summaries")
    if failed_summaries > 0:
        print(f"❌ Failed: {failed_summaries} summaries")
    print("\n📅 Check your 'Conversations' calendar for the all-day events!")
    
    return True

def parse_dates_from_args(args) -> List[date]:
    """Parse various date arguments and return a list of dates"""
    dates = []
    
    # Handle --last N days
    if args.last:
        today = datetime.now().date()
        for i in range(1, args.last + 1):
            dates.append(today - timedelta(days=i))
        return sorted(dates)
    
    # Handle date range --from and --to
    if args.from_date or args.to_date:
        if args.from_date:
            from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()
        else:
            from_date = datetime.now().date() - timedelta(days=1)
        
        if args.to_date:
            to_date = datetime.strptime(args.to_date, '%Y-%m-%d').date()
        else:
            to_date = from_date
        
        current = from_date
        while current <= to_date:
            dates.append(current)
            current += timedelta(days=1)
        return sorted(dates)
    
    # Handle multiple specific dates
    if args.dates:
        for date_str in args.dates:
            try:
                # Try negative number first
                days_ago = int(date_str)
                if days_ago <= 0:
                    target_date = datetime.now().date() + timedelta(days=days_ago)
                    dates.append(target_date)
                else:
                    print(f"⚠️ Ignoring positive number {days_ago} (use negative for days ago)")
            except ValueError:
                # Try parsing as YYYY-MM-DD
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    dates.append(target_date)
                except ValueError:
                    print(f"⚠️ Ignoring invalid date format: '{date_str}'")
        
        if dates:
            return sorted(dates)
    
    # Default to yesterday
    return [datetime.now().date() - timedelta(days=1)]

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create daily summary all-day events for dates with existing conversation events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool creates comprehensive all-day summary events for dates that already have
individual conversation events logged. Perfect for:
  • Adding summaries retrospectively
  • Days processed without --daily-summary flag
  • Creating overview events for better calendar organization

Examples:
  # Create summary for yesterday
  python3 create_daily_summaries.py
  
  # Create summaries for last 7 days
  python3 create_daily_summaries.py --last 7
  
  # Create summaries for specific dates
  python3 create_daily_summaries.py 2025-08-20 2025-08-21 2025-08-22
  
  # Create summaries for a date range
  python3 create_daily_summaries.py --from 2025-08-15 --to 2025-08-20
  
  # Force recreate existing summaries
  python3 create_daily_summaries.py --last 7 --force
        """
    )
    
    parser.add_argument(
        'dates',
        nargs='*',
        help='Specific dates to process (YYYY-MM-DD format or negative numbers for days ago)'
    )
    
    parser.add_argument(
        '--last',
        type=int,
        metavar='N',
        help='Process the last N days'
    )
    
    parser.add_argument(
        '--from',
        dest='from_date',
        metavar='DATE',
        help='Start date for range (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--to',
        dest='to_date',
        metavar='DATE',
        help='End date for range (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Recreate summaries even if they already exist'
    )
    
    args = parser.parse_args()
    
    # Parse dates from arguments
    dates_to_process = parse_dates_from_args(args)
    
    if not dates_to_process:
        print("❌ No valid dates to process")
        sys.exit(1)
    
    # Create summaries
    success = create_summaries_for_dates(dates_to_process, skip_existing=not args.force)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
