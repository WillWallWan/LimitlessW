# 🚀 Limitless Todo Calendar Integration Setup

This tool extracts action items from your Limitless conversations and automatically creates Google Calendar events or Google Tasks.

## 🎯 What it does

- **Scans your conversations** for phrases like "I need to", "I'll follow up", "TODO", etc.
- **Categorizes todos** by urgency (today, tomorrow, this week, urgent) and type (work, personal, health, etc.)
- **Creates Google Calendar events** with appropriate timing and reminders
- **Creates Google Tasks** for your task management
- **Avoids duplicates** using smart deduplication

## 📋 Setup Instructions

### Step 1: Get Your Limitless API Key

1. Go to [limitless.ai/developers](https://limitless.ai/developers)
2. Sign up and get your API key
3. Set the environment variable:
   ```bash
   export LIMITLESS_API_KEY='your_api_key_here'
   ```

### Step 2: Set Up Google Calendar API

1. **Go to Google Cloud Console**
   - Visit: [console.cloud.google.com](https://console.cloud.google.com/)

2. **Create or Select a Project**
   - Create a new project or select an existing one

3. **Enable APIs**
   - Enable "Google Calendar API"
   - Enable "Google Tasks API"

4. **Create Credentials**
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the credentials file

5. **Save Credentials**
   - Rename the downloaded file to `credentials.json`
   - Place it in this directory (same folder as this script)

### Step 3: Install Dependencies

```bash
# Create virtual environment (if not already done)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Run the Tool

```bash
source venv/bin/activate
python3 limitless_todo_calendar.py
```

## 🎮 How to Use

1. **Run the script** - It will scan your recent conversations
2. **Review extracted todos** - Preview what action items were found
3. **Choose format**:
   - Calendar events (with time blocks)
   - Google Tasks (task list)
   - Both
4. **Authenticate** - Browser will open for Google OAuth (first time only)
5. **Done!** - Check your calendar and tasks

## 📊 Example Output

```
🚀 Limitless Todo Calendar Integration
==================================================

🔍 Step 1: Extracting todos from recent conversations...
📚 Found 25 recent conversations
📝 Extracted 12 potential action items
✨ After deduplication: 8 unique todos

📋 Preview of extracted todos:
  1. [TODAY] call the dentist to schedule cleaning
  2. [URGENT] follow up on the project proposal
  3. [THIS_WEEK] buy groceries for the weekend
  4. [NORMAL] research vacation destinations
  5. [TOMORROW] send thank you email to client
  ... and 3 more

📅 Step 2: Creating calendar events/tasks...
Create calendar items for 8 todos? (y/n): y

🔐 Step 3: Authenticating with Google Calendar...
✅ Successfully authenticated with Google APIs

🔧 Step 4: How would you like to create todos?
1. Calendar events (with time blocks)
2. Google Tasks (task list)
3. Both
Enter choice (1/2/3): 3

⚡ Creating calendar items...
Processing 1/8: call the dentist to schedule cleaning...
📅 Created calendar event: https://calendar.google.com/...
✅ Created Google Task: call the dentist to schedule cleaning

🎉 Todo Calendar Integration Complete!
==================================================
📊 Summary:
  • Conversations analyzed: 25
  • Todos extracted: 8
  • Calendar events created: 8
  • Google Tasks created: 8

📅 Check your Google Calendar for the new events!
✅ Check Google Tasks (tasks.google.com) for your new tasks!
```

## 🔧 Customization

### Modify Action Patterns
Edit `todo_tracker.py` to add your own patterns:
```python
self.action_patterns = [
    r"I need to (.+?)(?:\.|$|,|\n)",
    r"Your custom pattern here (.+?)(?:\.|$|,|\n)",
]
```

### Adjust Timing
Edit `google_calendar_integration.py` to change when events are scheduled:
```python
def _get_event_time(self, urgency: str) -> datetime:
    # Customize timing logic here
```

### Change Categories
Edit category patterns to match your workflow:
```python
self.category_patterns = {
    'work': r'\b(meeting|email|call|project)\b',
    'personal': r'\b(family|friend|groceries)\b',
    # Add your categories here
}
```

## 🐛 Troubleshooting

### "No module named 'google.auth'"
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### "credentials.json not found"
1. Download OAuth credentials from Google Cloud Console
2. Rename to `credentials.json`
3. Place in the same directory as the script

### "No todos found"
- Make sure your conversations contain action phrases
- Try phrases like: "I need to", "I'll", "TODO", "follow up"
- Check that your Limitless device is recording conversations

### "API quota exceeded"
- Google APIs have usage limits
- Wait a bit or increase quotas in Google Cloud Console

## 📚 What's Next?

- **Run regularly** - Add to cron job for daily extraction
- **Customize patterns** - Add your own action item phrases
- **Integration** - Connect to other task managers (Notion, Todoist, etc.)
- **Analytics** - Track completion rates and productivity patterns

## 🤝 Contributing

Found a bug or want to add features? The code is modular and easy to extend!

- `todo_tracker.py` - Action item extraction logic
- `google_calendar_integration.py` - Google APIs integration
- `limitless_todo_calendar.py` - Main orchestration script


