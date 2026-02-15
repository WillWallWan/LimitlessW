import os
import json
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Google Calendar imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarTodoManager:
    """Manage todos by creating Google Calendar events and Google Tasks"""
    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/tasks'
    ]
    
    def __init__(self):
        self.calendar_service = None
        self.tasks_service = None
        self.credentials_file = 'credentials.json'  # Download from Google Cloud Console
        self.token_file = 'token.pickle'
        
    def authenticate(self):
        """Authenticate with Google APIs"""
        from google.auth.exceptions import RefreshError
        import time
        
        creds = None
        is_headless = os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, try to refresh
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Try refreshing with retries (token refresh can be flaky)
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        print(f"🔄 Refreshing Google OAuth token (attempt {attempt}/{max_retries})...")
                        creds.refresh(Request())
                        print(f"✅ Token refreshed successfully")
                        break
                    except RefreshError as e:
                        if attempt < max_retries:
                            print(f"⚠️  Refresh attempt {attempt} failed: {e}")
                            time.sleep(2 * attempt)
                        else:
                            print(f"❌ Token refresh failed after {max_retries} attempts: {e}")
                            if is_headless:
                                print(f"❌ Running in CI/headless mode - cannot open browser for re-auth")
                                print(f"   Please update GOOGLE_TOKEN_PICKLE secret with a fresh token")
                                return False
                            # Only fall through to browser auth locally
                            print(f"⚠️  Token expired or revoked. Re-authenticating...")
                            os.remove(self.token_file)
                            creds = None
                    except Exception as e:
                        if attempt < max_retries:
                            print(f"⚠️  Refresh attempt {attempt} failed: {e}")
                            time.sleep(2 * attempt)
                        else:
                            print(f"❌ Unexpected error refreshing token: {e}")
                            if is_headless:
                                return False
                            os.remove(self.token_file)
                            creds = None
            
            # If still no valid creds, run the OAuth flow (only works locally)
            if not creds or not creds.valid:
                if is_headless:
                    print(f"❌ No valid credentials and cannot open browser in CI mode")
                    print(f"   Please run locally first, then update GOOGLE_TOKEN_PICKLE secret")
                    return False
                    
                if not os.path.exists(self.credentials_file):
                    print(f"❌ Please download OAuth credentials from Google Cloud Console")
                    print(f"   Save them as '{self.credentials_file}' in this directory")
                    print(f"   Instructions: https://developers.google.com/calendar/api/quickstart/python")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build services
        try:
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            self.tasks_service = build('tasks', 'v1', credentials=creds)
            print("✅ Successfully authenticated with Google APIs")
            return True
        except Exception as e:
            print(f"❌ Failed to authenticate: {e}")
            return False
    
    def create_calendar_event(self, todo: Dict, calendar_id: str = 'primary') -> Optional[str]:
        """Create a calendar event for a todo item"""
        if not self.calendar_service:
            print("❌ Calendar service not authenticated")
            return None
        
        # Determine event time based on urgency
        event_time = self._get_event_time(todo['urgency'])
        
        event = {
            'summary': f"TODO: {todo['text']}",
            'description': f"""
Action Item from Conversation

📋 Task: {todo['text']}
🏷️ Category: {todo['category']}
⚡ Urgency: {todo['urgency']}
📅 From: {todo['lifelog_title']}
🕐 Mentioned: {todo['source_time']}

Context: {todo['full_context']}
            """.strip(),
            'start': {
                'dateTime': event_time.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Adjust to your timezone
            },
            'end': {
                'dateTime': (event_time + timedelta(minutes=30)).isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        
        try:
            event_result = self.calendar_service.events().insert(
                calendarId=calendar_id, body=event).execute()
            print(f"📅 Created calendar event: {event_result.get('htmlLink')}")
            return event_result.get('id')
        except HttpError as error:
            print(f"❌ Failed to create calendar event: {error}")
            return None
    
    def create_google_task(self, todo: Dict, tasklist_id: str = '@default') -> Optional[str]:
        """Create a Google Task for a todo item"""
        if not self.tasks_service:
            print("❌ Tasks service not authenticated")
            return None
        
        # Determine due date based on urgency
        due_date = self._get_due_date(todo['urgency'])
        
        task = {
            'title': todo['text'],
            'notes': f"""
Category: {todo['category']}
Urgency: {todo['urgency']}
From conversation: {todo['lifelog_title']}
Mentioned at: {todo['source_time']}

Context: {todo['full_context']}
            """.strip(),
        }
        
        if due_date:
            task['due'] = due_date.isoformat() + 'Z'
        
        try:
            task_result = self.tasks_service.tasks().insert(
                tasklist=tasklist_id, body=task).execute()
            print(f"✅ Created Google Task: {task_result.get('title')}")
            return task_result.get('id')
        except HttpError as error:
            print(f"❌ Failed to create Google Task: {error}")
            return None
    
    def _get_event_time(self, urgency: str) -> datetime:
        """Get appropriate event time based on urgency"""
        now = datetime.now()
        
        if urgency == 'today':
            # Schedule for later today
            return now.replace(hour=17, minute=0, second=0, microsecond=0)
        elif urgency == 'tomorrow':
            # Schedule for tomorrow morning
            return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        elif urgency == 'this_week':
            # Schedule for Friday
            days_until_friday = (4 - now.weekday()) % 7
            if days_until_friday == 0 and now.hour > 17:
                days_until_friday = 7
            return (now + timedelta(days=days_until_friday)).replace(hour=15, minute=0, second=0, microsecond=0)
        elif urgency == 'urgent':
            # Schedule for 1 hour from now
            return now + timedelta(hours=1)
        else:
            # Default: next Monday morning
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            return (now + timedelta(days=days_until_monday)).replace(hour=9, minute=0, second=0, microsecond=0)
    
    def _get_due_date(self, urgency: str) -> Optional[datetime]:
        """Get appropriate due date based on urgency"""
        now = datetime.now()
        
        if urgency == 'today':
            return now.replace(hour=23, minute=59, second=59, microsecond=0)
        elif urgency == 'tomorrow':
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
        elif urgency == 'this_week':
            # Due end of this week
            days_until_sunday = (6 - now.weekday()) % 7
            return (now + timedelta(days=days_until_sunday)).replace(hour=23, minute=59, second=59, microsecond=0)
        elif urgency == 'urgent':
            return now + timedelta(hours=2)
        else:
            # Default: due in one week
            return now + timedelta(days=7)
    
    def get_calendar_list(self) -> List[Dict]:
        """Get list of available calendars"""
        if not self.calendar_service:
            return []
        
        try:
            calendar_list = self.calendar_service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except HttpError as error:
            print(f"❌ Failed to get calendar list: {error}")
            return []
    
    def get_task_lists(self) -> List[Dict]:
        """Get list of available task lists"""
        if not self.tasks_service:
            return []
        
        try:
            task_lists = self.tasks_service.tasklists().list().execute()
            return task_lists.get('items', [])
        except HttpError as error:
            print(f"❌ Failed to get task lists: {error}")
            return []
    
    def create_calendar(self, name: str, description: str = "", color: str = "8") -> Optional[str]:
        """Create a new calendar and return its ID"""
        if not self.calendar_service:
            print("❌ Calendar service not authenticated")
            return None
        
        calendar = {
            'summary': name,
            'description': description,
            'timeZone': 'America/Los_Angeles'  # Adjust to your timezone
        }
        
        try:
            created_calendar = self.calendar_service.calendars().insert(body=calendar).execute()
            calendar_id = created_calendar.get('id')
            
            # Set the calendar color
            calendar_list_entry = {
                'id': calendar_id,
                'colorId': color  # Light blue
            }
            
            self.calendar_service.calendarList().update(
                calendarId=calendar_id, 
                body=calendar_list_entry
            ).execute()
            
            print(f"✅ Created calendar: {name} (ID: {calendar_id})")
            return calendar_id
            
        except HttpError as error:
            print(f"❌ Failed to create calendar: {error}")
            return None
    
    def find_calendar_by_name(self, name: str) -> Optional[str]:
        """Find a calendar by name and return its ID"""
        calendars = self.get_calendar_list()
        
        for calendar in calendars:
            if calendar.get('summary', '').lower() == name.lower():
                return calendar.get('id')
        
        return None
    
    def get_or_create_conversations_calendar(self) -> Optional[str]:
        """Get or create the 'Conversations' calendar"""
        
        # First, try to find existing calendar
        calendar_id = self.find_calendar_by_name("Conversations")
        
        if calendar_id:
            print(f"📅 Found existing 'Conversations' calendar")
            return calendar_id
        
        # Create new calendar
        print(f"🆕 Creating new 'Conversations' calendar...")
        calendar_id = self.create_calendar(
            name="Conversations",
            description="Auto-generated conversation logs from Limitless",
            color="8"  # Light blue
        )
        
        return calendar_id

def process_todos_to_calendar(todos_file: str = 'extracted_todos.json'):
    """Main function to process extracted todos and create calendar events"""
    
    if not os.path.exists(todos_file):
        print(f"❌ No todos file found: {todos_file}")
        print("   Run todo_tracker.py first to extract todos")
        return
    
    # Load todos
    with open(todos_file, 'r') as f:
        todos = json.load(f)
    
    if not todos:
        print("📭 No todos found in file")
        return
    
    print(f"📋 Found {len(todos)} todos to process")
    
    # Initialize Google Calendar manager
    calendar_manager = GoogleCalendarTodoManager()
    
    if not calendar_manager.authenticate():
        return
    
    # Ask user preference
    print("\n🔧 How would you like to create todos?")
    print("1. Calendar events (with time blocks)")
    print("2. Google Tasks (task list)")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    created_events = 0
    created_tasks = 0
    
    # Process each todo
    for i, todo in enumerate(todos, 1):
        print(f"\n--- Processing Todo {i}/{len(todos)} ---")
        print(f"📋 {todo['text'][:50]}{'...' if len(todo['text']) > 50 else ''}")
        
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
    
    print(f"\n🎉 Processing complete!")
    print(f"📅 Created {created_events} calendar events")
    print(f"✅ Created {created_tasks} Google Tasks")

if __name__ == "__main__":
    process_todos_to_calendar()
