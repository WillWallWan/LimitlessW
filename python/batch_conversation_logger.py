#!/usr/bin/env python3
"""
Batch Conversation Logger for Limitless API + Google Calendar

Enhanced version that supports processing multiple days at once:
- Date ranges (--from and --to)
- Multiple specific dates
- Last N days (--last)
- Progress tracking and error recovery
- Summary report after batch processing
"""

import os
import json
import time
import sys
import argparse
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Tuple
from dotenv import load_dotenv
import anthropic
from _client import get_lifelogs
from google_calendar_integration import GoogleCalendarTodoManager

# Load environment variables
load_dotenv()

# Import functions from individual logger
from individual_conversation_logger import (
    summarize_individual_conversation,
    create_individual_calendar_event,
    clear_existing_events
)

class BatchConversationLogger:
    """Batch processor for logging multiple days of conversations"""
    
    def __init__(self):
        self.api_key = os.getenv('LIMITLESS_API_KEY')
        self.calendar_manager = None
        self.conversations_calendar_id = None
        self.stats = {
            'total_days': 0,
            'successful_days': 0,
            'failed_days': 0,
            'total_conversations': 0,
            'total_events_created': 0,
            'errors': []
        }
    
    def initialize(self):
        """Initialize API keys and Google Calendar"""
        if not self.api_key:
            print("❌ LIMITLESS_API_KEY not found in .env file")
            return False
        
        print("📅 Setting up Google Calendar integration...")
        self.calendar_manager = GoogleCalendarTodoManager()
        if not self.calendar_manager.authenticate():
            print("❌ Failed to authenticate with Google Calendar")
            return False
        
        # Get or create the Conversations calendar
        self.conversations_calendar_id = self.calendar_manager.get_or_create_conversations_calendar()
        if not self.conversations_calendar_id:
            print("❌ Failed to create/find Conversations calendar")
            return False
        
        return True
    
    def process_single_day(self, target_date: date) -> Tuple[bool, int, int]:
        """Process a single day's conversations. Returns (success, events_created, conversations_found)"""
        date_str = target_date.strftime('%Y-%m-%d')
        
        try:
            # Fetch lifelogs from target date
            lifelogs = get_lifelogs(
                api_key=self.api_key,
                date=date_str,
                includeMarkdown=True,
                limit=100
            )
            
            if not lifelogs:
                return True, 0, 0  # No data is not an error
            
            # Filter meaningful conversations (>30 seconds)
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
                return True, 0, len(lifelogs)
            
            # Clear existing events for this date
            clear_existing_events(self.calendar_manager, self.conversations_calendar_id, target_date)
            
            # Process each conversation
            created_count = 0
            for i, lifelog in enumerate(meaningful_conversations, 1):
                title = lifelog.get('title', 'Untitled')
                markdown = lifelog.get('markdown', '')
                
                # Summarize with Claude
                summary = summarize_individual_conversation(markdown, title)
                
                # Create calendar event
                event_id = create_individual_calendar_event(
                    lifelog, summary, self.calendar_manager, self.conversations_calendar_id
                )
                
                if event_id:
                    created_count += 1
                
                # Rate limiting
                if i < len(meaningful_conversations):
                    time.sleep(3)
            
            return True, created_count, len(meaningful_conversations)
            
        except Exception as e:
            self.stats['errors'].append(f"{date_str}: {str(e)}")
            return False, 0, 0
    
    def process_dates(self, dates: List[date]):
        """Process multiple dates with progress tracking"""
        self.stats['total_days'] = len(dates)
        
        print(f"\n🚀 Starting batch processing of {len(dates)} day(s)")
        print("=" * 60)
        
        for i, target_date in enumerate(dates, 1):
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
            
            print(f"\n📆 [{i}/{len(dates)}] Processing {date_str} ({date_desc})")
            print("-" * 40)
            
            # Process the day
            success, events_created, conversations_found = self.process_single_day(target_date)
            
            if success:
                self.stats['successful_days'] += 1
                self.stats['total_events_created'] += events_created
                self.stats['total_conversations'] += conversations_found
                
                if conversations_found == 0:
                    print(f"   ⚪ No conversations found")
                elif events_created == 0:
                    print(f"   🟡 Found {conversations_found} conversations but none were meaningful (>30s)")
                else:
                    print(f"   ✅ Created {events_created} events from {conversations_found} conversations")
            else:
                self.stats['failed_days'] += 1
                print(f"   ❌ Failed to process day")
            
            # Brief pause between days
            if i < len(dates):
                time.sleep(1)
        
        # Print summary report
        self.print_summary_report()
    
    def print_summary_report(self):
        """Print a summary report of the batch processing"""
        print("\n" + "=" * 60)
        print("📊 BATCH PROCESSING SUMMARY")
        print("=" * 60)
        
        print(f"\n📅 Days Processed:")
        print(f"   • Total: {self.stats['total_days']}")
        print(f"   • Successful: {self.stats['successful_days']} ✅")
        if self.stats['failed_days'] > 0:
            print(f"   • Failed: {self.stats['failed_days']} ❌")
        
        print(f"\n💬 Conversations:")
        print(f"   • Total Found: {self.stats['total_conversations']}")
        print(f"   • Events Created: {self.stats['total_events_created']}")
        
        if self.stats['total_conversations'] > 0:
            avg_per_day = self.stats['total_events_created'] / max(self.stats['successful_days'], 1)
            print(f"   • Average per Day: {avg_per_day:.1f}")
        
        if self.stats['errors']:
            print(f"\n⚠️ Errors Encountered:")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.stats['errors']) > 5:
                print(f"   • ... and {len(self.stats['errors']) - 5} more")
        
        print("\n" + "=" * 60)
        print("✨ Batch processing complete! Check your 'Conversations' calendar.")
        print("=" * 60)


def parse_dates_from_args(args) -> List[date]:
    """Parse various date arguments and return a list of dates to process"""
    dates = []
    
    # Handle --last N days
    if args.last:
        today = datetime.now().date()
        for i in range(1, args.last + 1):
            dates.append(today - timedelta(days=i))
        return sorted(dates)
    
    # Handle date range --from and --to
    if args.from_date or args.to_date:
        # Default from_date to yesterday if not specified
        if args.from_date:
            from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()
        else:
            from_date = datetime.now().date() - timedelta(days=1)
        
        # Default to_date to from_date if not specified (single day)
        if args.to_date:
            to_date = datetime.strptime(args.to_date, '%Y-%m-%d').date()
        else:
            to_date = from_date
        
        # Generate all dates in range
        current = from_date
        while current <= to_date:
            dates.append(current)
            current += timedelta(days=1)
        return sorted(dates)
    
    # Handle multiple specific dates
    if args.dates:
        for date_str in args.dates:
            # Support both YYYY-MM-DD and negative numbers for days ago
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
    
    # Default to yesterday if no dates specified
    return [datetime.now().date() - timedelta(days=1)]


def main():
    """Main entry point for batch conversation logger"""
    parser = argparse.ArgumentParser(
        description="Batch log conversations from Limitless to Google Calendar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process yesterday (default)
  python3 batch_conversation_logger.py
  
  # Process last 7 days
  python3 batch_conversation_logger.py --last 7
  
  # Process specific date range
  python3 batch_conversation_logger.py --from 2025-08-15 --to 2025-08-20
  
  # Process multiple specific dates
  python3 batch_conversation_logger.py 2025-08-18 2025-08-19 2025-08-20
  
  # Mix formats: specific dates and days ago
  python3 batch_conversation_logger.py 2025-08-18 -3 -7
  
  # Process all of last week
  python3 batch_conversation_logger.py --from 2025-08-12 --to 2025-08-18
        """
    )
    
    # Add arguments for different date selection methods
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
        help='End date for range (YYYY-MM-DD format), defaults to --from date if not specified'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip days that already have events (not implemented yet)'
    )
    
    args = parser.parse_args()
    
    # Parse dates from arguments
    dates_to_process = parse_dates_from_args(args)
    
    if not dates_to_process:
        print("❌ No valid dates to process")
        sys.exit(1)
    
    # Create and initialize the batch logger
    logger = BatchConversationLogger()
    if not logger.initialize():
        sys.exit(1)
    
    # Process all dates
    logger.process_dates(dates_to_process)


if __name__ == "__main__":
    main()
