#!/usr/bin/env python3
"""
Enhanced Batch Conversation Logger with Rate Limit Handling

Features:
- Intelligent retry logic with exponential backoff
- Dynamic delays based on content size
- Graceful handling of rate limit errors
- Detailed error reporting and recovery
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
    get_individual_conversation_prompt,
    create_individual_calendar_event,
    clear_existing_events,
    get_existing_lifelog_ids
)

# Import daily summary functions
from daily_summary_calendar import (
    process_day_summary,
    clear_existing_daily_summary
)

class EnhancedBatchLogger:
    """Enhanced batch processor with intelligent rate limit handling"""
    
    def __init__(self, create_daily_summaries=False, summaries_only=False, force=False):
        self.api_key = os.getenv('LIMITLESS_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.calendar_manager = None
        self.conversations_calendar_id = None
        self.claude_client = None
        self.create_daily_summaries = create_daily_summaries
        self.summaries_only = summaries_only
        self.force = force  # If True, clear and recreate all events
        self.stats = {
            'total_days': 0,
            'successful_days': 0,
            'failed_days': 0,
            'total_conversations': 0,
            'total_events_created': 0,
            'skipped_duplicates': 0,  # Track skipped duplicates
            'daily_summaries_created': 0,
            'rate_limit_retries': 0,
            'failed_summaries': 0,
            'errors': []
        }
        # Rate limit management
        self.base_delay = 3  # Base delay between API calls
        self.current_delay = self.base_delay
        self.max_retries = 3
        self.backoff_multiplier = 2
        self.consecutive_errors = 0  # Track consecutive errors
        self.overload_cooldown = False  # Flag for server overload state
    
    def initialize(self):
        """Initialize API keys and services"""
        if not self.api_key:
            print("❌ LIMITLESS_API_KEY not found in .env file")
            return False
        
        if not self.anthropic_key:
            print("❌ ANTHROPIC_API_KEY not found in .env file")
            return False
        
        # Initialize Claude client
        self.claude_client = anthropic.Anthropic(api_key=self.anthropic_key)
        
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
    
    def estimate_token_count(self, text: str) -> int:
        """Rough estimation of token count (1 token ≈ 4 characters)"""
        return len(text) // 4
    
    def calculate_dynamic_delay(self, content: str) -> float:
        """Calculate delay based on content size to avoid rate limits"""
        tokens = self.estimate_token_count(content)
        
        # Adjust delay based on content size
        if tokens < 1000:
            return self.base_delay
        elif tokens < 5000:
            return self.base_delay * 1.5
        elif tokens < 10000:
            return self.base_delay * 2
        else:
            # Very long content (like performance transcripts)
            return self.base_delay * 3
    
    def summarize_with_retry(self, markdown: str, title: str, attempt: int = 1) -> Optional[Dict]:
        """Summarize conversation with intelligent retry logic"""
        try:
            # Generate the prompt
            prompt = get_individual_conversation_prompt(markdown, title)
            
            # Call Claude API
            print(f"      🤖 Calling Claude AI...")
            message = self.claude_client.messages.create(
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
            
            # Claude 4.5 often wraps JSON in markdown code blocks, so try extracting that first
            import re
            
            # Try to extract JSON from markdown code blocks first
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text, re.MULTILINE)
            if code_block_match:
                try:
                    summary_data = json.loads(code_block_match.group(1))
                    print(f"      ✅ Summary generated")
                    # Reset delay and error tracking on success
                    self.current_delay = self.base_delay
                    self.consecutive_errors = 0
                    self.overload_cooldown = False
                    return summary_data
                except json.JSONDecodeError:
                    pass
            
            # Try parsing as pure JSON (for older Claude models)
            try:
                summary_data = json.loads(response_text)
                print(f"      ✅ Summary generated")
                # Reset delay and error tracking on success
                self.current_delay = self.base_delay
                self.consecutive_errors = 0
                self.overload_cooldown = False
                return summary_data
            except json.JSONDecodeError:
                # Try other patterns as fallback
                json_patterns = [
                    r'\{[^{}]*"description"[^{}]*\}',  # Simple JSON with description
                    r'\{[\s\S]*?"description"[\s\S]*?\}(?=\s*$)',  # JSON at end of text
                    r'\{[\s\S]*\}'  # Last resort - any JSON-like structure
                ]
                
                json_match = None
                for pattern in json_patterns:
                    match = re.search(pattern, response_text, re.MULTILINE)
                    if match:
                        json_match = match
                        break
                
                if json_match:
                    try:
                        json_text = json_match.group(1) if json_match.groups() else json_match.group()
                        summary_data = json.loads(json_text)
                        print(f"      ✅ Summary generated")
                        return summary_data
                    except:
                        pass
                
                # Try to build a summary from the text content
                lines = response_text.strip().split('\n')
                description = ""
                
                # Look for key phrases in the response
                for line in lines:
                    if any(phrase in line.lower() for phrase in ['summary:', 'overview:', 'description:']):
                        description = line.split(':', 1)[-1].strip()
                        break
                
                if not description:
                    description = response_text[:200] + "..." if len(response_text) > 200 else response_text
                
                # Return a basic structure if JSON parsing fails
                return {
                    "description": description,
                    "key_information": "AI response was not properly formatted",
                    "decisions_made": "None", 
                    "problems_solutions": "None",
                    "people_involved": "None",
                    "conversation_type": "general"
                }
        
        except anthropic.RateLimitError as e:
            # Handle rate limit errors specifically
            if attempt <= self.max_retries:
                self.stats['rate_limit_retries'] += 1
                
                # Calculate backoff delay
                retry_delay = self.current_delay * (self.backoff_multiplier ** (attempt - 1))
                
                # Check if it's an acceleration limit
                if "usage increase rate" in str(e):
                    print(f"   ⏳ Rate acceleration limit hit. Waiting {retry_delay:.0f}s before retry {attempt}/{self.max_retries}...")
                    retry_delay = max(retry_delay, 30)  # Minimum 30s for acceleration limits
                else:
                    print(f"   ⏳ Rate limit hit. Waiting {retry_delay:.0f}s before retry {attempt}/{self.max_retries}...")
                
                time.sleep(retry_delay)
                
                # Increase delay for next call
                self.current_delay = min(self.current_delay * 1.5, 60)  # Cap at 60 seconds
                
                # Retry
                return self.summarize_with_retry(markdown, title, attempt + 1)
            else:
                print(f"   ❌ Max retries exceeded for '{title}'")
                self.stats['failed_summaries'] += 1
                return None
        
        except Exception as e:
            # Handle Anthropic overloaded errors (529) and other API errors
            error_str = str(e)
            
            # Check for overloaded error or other retryable conditions
            if any(err in error_str.lower() for err in ['overloaded', '529', 'timeout', 'connection']):
                self.consecutive_errors += 1
                self.overload_cooldown = True
                
                if attempt <= self.max_retries:
                    # Longer delay for overloaded errors
                    retry_delay = 30 * attempt  # 30s, 60s, 90s
                    print(f"   ⏳ Server overloaded. Waiting {retry_delay}s before retry {attempt}/{self.max_retries}...")
                    time.sleep(retry_delay)
                    return self.summarize_with_retry(markdown, title, attempt + 1)
            
            # For non-retryable errors, log and return None
            print(f"❌ Error summarizing '{title}': {e}")
            self.stats['errors'].append(f"Summary failed for '{title}': {error_str}")
            return None
    
    def process_single_day(self, target_date: date) -> Tuple[bool, int, int]:
        """Process a single day's conversations with enhanced error handling"""
        date_str = target_date.strftime('%Y-%m-%d')
        
        try:
            # Fetch lifelogs from target date
            print(f"   🔍 Fetching ALL conversations from Limitless API...")
            print(f"   ⏳ This may take 2-5 minutes with large amounts of data...")
            lifelogs = get_lifelogs(
                api_key=self.api_key,
                date=date_str,
                includeMarkdown=True,
                limit=None  # Fetch ALL conversations (no limit)
            )
            print(f"   📥 Received {len(lifelogs) if lifelogs else 0} total recordings")
            
            if not lifelogs:
                return True, 0, 0, 0  # No data is not an error
            
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
                return True, 0, len(lifelogs), 0
            
            print(f"   📋 Found {len(meaningful_conversations)} conversations >30s")
            
            # Get existing lifelog IDs to skip duplicates (unless --force is used)
            existing_ids = set()
            if not self.summaries_only:
                if self.force:
                    # Force mode: clear all existing events
                    print(f"   🗑️  Force mode: Clearing existing calendar events...")
                    clear_existing_events(self.calendar_manager, self.conversations_calendar_id, target_date)
                else:
                    # Normal mode: get existing IDs to skip duplicates
                    print(f"   🔍 Checking for existing events...")
                    existing_ids = get_existing_lifelog_ids(self.calendar_manager, self.conversations_calendar_id, target_date)
                    if existing_ids:
                        print(f"   📋 Found {len(existing_ids)} existing events, will skip duplicates")
            
            # If daily summaries enabled, clear existing daily summary too (only in force mode or if creating summaries)
            if (self.create_daily_summaries or self.summaries_only) and self.force:
                clear_existing_daily_summary(self.calendar_manager, self.conversations_calendar_id, target_date)
            
            # Process each conversation with intelligent rate limiting (skip if summaries only)
            created_count = 0
            skipped_count = 0
            if not self.summaries_only:
                for i, lifelog in enumerate(meaningful_conversations, 1):
                    title = lifelog.get('title', 'Untitled')
                    markdown = lifelog.get('markdown', '')
                    lifelog_id = lifelog.get('id', '')
                    
                    # Skip if this lifelog already has a calendar event
                    if lifelog_id and lifelog_id in existing_ids:
                        print(f"   [{i}/{len(meaningful_conversations)}] ⏭️  Skipping (already exists): {title[:40]}...")
                        skipped_count += 1
                        self.stats['skipped_duplicates'] += 1
                        continue
                    
                    print(f"   [{i}/{len(meaningful_conversations)}] Processing: {title[:50]}...")
                    
                    # Summarize with retry logic
                    summary = self.summarize_with_retry(markdown, title)
                    
                    # Create calendar event (even if summary failed)
                    event_id = create_individual_calendar_event(
                        lifelog, summary, self.calendar_manager, self.conversations_calendar_id
                    )
                    
                    if event_id:
                        created_count += 1
                    
                    # Dynamic delay based on content size and current rate limit status
                    if i < len(meaningful_conversations):
                        delay = self.calculate_dynamic_delay(markdown)
                        
                        # If we're in overload cooldown, add extra delay
                        if self.overload_cooldown:
                            delay = max(delay * 2, 10)  # Double delay, minimum 10s
                            
                        # If we've had multiple consecutive errors, be more conservative
                        if self.consecutive_errors > 2:
                            delay = max(delay, 15)  # Minimum 15s after multiple errors
                        
                        # Use the maximum of calculated delay and current delay
                        actual_delay = max(delay, self.current_delay)
                        time.sleep(actual_delay)
            
            # Create daily summary if enabled
            if (self.create_daily_summaries or self.summaries_only) and meaningful_conversations:
                print(f"   📊 Creating daily summary...")
                if process_day_summary(
                    meaningful_conversations, 
                    target_date, 
                    self.calendar_manager, 
                    self.conversations_calendar_id
                ):
                    self.stats['daily_summaries_created'] += 1
                    print(f"   ✅ Daily summary created")
                else:
                    print(f"   ⚠️ Failed to create daily summary")
            
            return True, created_count, len(meaningful_conversations), skipped_count
            
        except Exception as e:
            self.stats['errors'].append(f"{date_str}: {str(e)}")
            return False, 0, 0, 0
    
    def process_dates(self, dates: List[date]):
        """Process multiple dates with enhanced progress tracking"""
        self.stats['total_days'] = len(dates)
        
        print(f"\n🚀 Starting enhanced batch processing of {len(dates)} day(s)")
        print("📊 Rate limit protection: ✅ Enabled")
        print("🔄 Auto-retry on errors: ✅ Enabled")
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
            
            # Show server status if in cooldown
            if self.overload_cooldown:
                print("   ⚠️ Server stress detected - using conservative delays")
            
            # Process the day
            success, events_created, conversations_found, skipped = self.process_single_day(target_date)
            
            if success:
                self.stats['successful_days'] += 1
                self.stats['total_events_created'] += events_created
                self.stats['total_conversations'] += conversations_found
                
                if conversations_found == 0:
                    print(f"   ⚪ No conversations found")
                elif self.summaries_only:
                    print(f"   📊 Processed {conversations_found} conversations for daily summary")
                elif events_created == 0 and skipped == 0:
                    print(f"   🟡 Found {conversations_found} conversations but none were meaningful (>30s)")
                elif events_created == 0 and skipped > 0:
                    print(f"   ⏭️  All {skipped} conversations already exist, nothing new to add")
                else:
                    skip_msg = f", skipped {skipped} duplicates" if skipped > 0 else ""
                    print(f"   ✅ Created {events_created} events from {conversations_found} conversations{skip_msg}")
                    if self.stats['rate_limit_retries'] > 0:
                        print(f"   🔄 Handled {self.stats['rate_limit_retries']} rate limit retries")
            else:
                self.stats['failed_days'] += 1
                print(f"   ❌ Failed to process day")
            
            # Brief pause between days
            if i < len(dates):
                time.sleep(1)
        
        # Print enhanced summary report
        self.print_summary_report()
    
    def print_summary_report(self):
        """Print an enhanced summary report with rate limit stats"""
        print("\n" + "=" * 60)
        print("📊 ENHANCED BATCH PROCESSING SUMMARY")
        print("=" * 60)
        
        print(f"\n📅 Days Processed:")
        print(f"   • Total: {self.stats['total_days']}")
        print(f"   • Successful: {self.stats['successful_days']} ✅")
        if self.stats['failed_days'] > 0:
            print(f"   • Failed: {self.stats['failed_days']} ❌")
        
        if not self.summaries_only:
            print(f"\n💬 Conversations:")
            print(f"   • Total Found: {self.stats['total_conversations']}")
            print(f"   • Events Created: {self.stats['total_events_created']}")
            if self.stats['skipped_duplicates'] > 0:
                print(f"   • Skipped (duplicates): {self.stats['skipped_duplicates']}")
            
            if self.stats['total_conversations'] > 0:
                avg_per_day = self.stats['total_events_created'] / max(self.stats['successful_days'], 1)
                print(f"   • Average per Day: {avg_per_day:.1f}")
                # Adjust success rate to account for skipped duplicates
                processed = self.stats['total_events_created'] + self.stats['skipped_duplicates']
                if processed > 0:
                    new_rate = (self.stats['total_events_created'] / self.stats['total_conversations']) * 100
                    print(f"   • New Events Rate: {new_rate:.1f}%")
        
        print(f"\n🚦 Rate Limit Management:")
        print(f"   • Automatic Retries: {self.stats['rate_limit_retries']}")
        if self.stats['failed_summaries'] > 0:
            print(f"   • Failed Summaries: {self.stats['failed_summaries']} (created with basic titles)")
        
        if self.create_daily_summaries:
            print(f"\n📅 Daily Summaries:")
            print(f"   • Created: {self.stats['daily_summaries_created']} all-day events")
        
        if self.stats['errors']:
            print(f"\n⚠️ Errors Encountered:")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.stats['errors']) > 5:
                print(f"   • ... and {len(self.stats['errors']) - 5} more")
        
        print("\n" + "=" * 60)
        print("✨ Enhanced batch processing complete!")
        print("📅 Check your 'Conversations' calendar for the results.")
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
    """Main entry point for enhanced batch conversation logger"""
    parser = argparse.ArgumentParser(
        description="Enhanced batch log conversations with intelligent rate limit handling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Enhanced Features:
  ✅ Automatic retry with exponential backoff on rate limits
  ✅ Dynamic delays based on conversation length
  ✅ Graceful degradation (creates events even if AI summary fails)
  ✅ Detailed progress and error reporting
  ✅ Optional daily summary all-day events
  ✅ Duplicate detection - skips conversations already in calendar
  ✅ --force flag to override and recreate all events

Examples:
  # Process yesterday (default)
  python3 batch_conversation_logger.py
  
  # Process last 7 days with daily summaries
  python3 batch_conversation_logger.py --last 7 --daily-summary
  
  # Process specific date range
  python3 batch_conversation_logger.py --from 2025-08-15 --to 2025-08-20
  
  # Process multiple dates with daily summaries
  python3 batch_conversation_logger.py 2025-08-18 2025-08-19 --daily-summary
  
  # Create ONLY daily summaries (no individual events)
  python3 batch_conversation_logger.py --last 7 --summaries-only
  
  # Force recreate all events (ignores duplicates, clears existing)
  python3 batch_conversation_logger.py --last 7 --force
  
  # Mix formats: specific dates and days ago
  python3 batch_conversation_logger.py 2025-08-18 -3 -7
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
        '--daily-summary',
        action='store_true',
        help='Create all-day summary events for each processed day'
    )
    
    parser.add_argument(
        '--summaries-only',
        action='store_true',
        help='Only create daily summaries, skip individual conversation events'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recreate all events (clear existing and recreate, ignoring duplicates)'
    )
    
    args = parser.parse_args()
    
    # Parse dates from arguments
    dates_to_process = parse_dates_from_args(args)
    
    if not dates_to_process:
        print("❌ No valid dates to process")
        sys.exit(1)
    
    # Handle summaries_only logic
    if args.summaries_only:
        # If summaries_only is set, we always create daily summaries
        create_daily_summaries = True
        print("🗓️ Running in summaries-only mode (skipping individual conversation events)")
    else:
        create_daily_summaries = args.daily_summary
    
    # Create and initialize the enhanced logger
    logger = EnhancedBatchLogger(
        create_daily_summaries=create_daily_summaries,
        summaries_only=args.summaries_only,
        force=args.force
    )
    if not logger.initialize():
        sys.exit(1)
    
    # Process all dates with enhanced rate limit handling
    logger.process_dates(dates_to_process)


if __name__ == "__main__":
    main()
